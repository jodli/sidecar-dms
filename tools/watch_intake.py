"""Watch intake folder for new PDFs and process them automatically."""

import asyncio
import time
from pathlib import Path

from config import INTAKE_DIR, get_logger
from process_pdf import process, rebuild

log = get_logger("watch")

POLL_INTERVAL = 2   # seconds
SETTLE_POLLS = 3    # number of stable size checks before processing
SETTLE_INTERVAL = 1 # seconds between settle checks
RETRY_AFTER = 300   # seconds before retrying a failed file


async def watch_async(stop: asyncio.Event):
    """Poll intake dir, process settled PDFs in batches until stop is set.

    Blocking I/O (glob, stat, time.sleep in is_settled, OCR in process)
    runs via asyncio.to_thread() to keep the event loop responsive.
    """
    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Watching %s (poll %ds, settle %d×%ds)", INTAKE_DIR, POLL_INTERVAL, SETTLE_POLLS, SETTLE_INTERVAL)

    failed: dict[str, float] = {}

    while not stop.is_set():
        batch = await asyncio.to_thread(collect_batch, INTAKE_DIR, failed)

        if batch:
            log.info("Batch: %d PDFs", len(batch))
            processed = 0
            for i, pdf in enumerate(batch, 1):
                if stop.is_set():
                    break
                try:
                    result = await asyncio.to_thread(process, pdf)
                    processed += 1
                    log.info("[%d/%d] %s → %s", i, len(batch), pdf.name, result.name)
                except Exception:
                    log.exception("[%d/%d] FEHLER %s", i, len(batch), pdf.name)
                    failed[pdf.name] = time.time()

            if processed:
                await asyncio.to_thread(rebuild)
                log.info("Batch fertig: %d verarbeitet", processed)

        try:
            await asyncio.wait_for(stop.wait(), timeout=POLL_INTERVAL)
            return  # stop was set while waiting
        except asyncio.TimeoutError:
            continue  # next poll iteration


def collect_batch(intake_dir: Path, failed: dict[str, float]) -> list[Path]:
    """Collect all settled, non-failed PDFs from intake."""
    now = time.time()
    batch = []
    for pdf in sorted(intake_dir.glob("*.pdf")):
        if pdf.name in failed and now - failed[pdf.name] < RETRY_AFTER:
            continue
        if pdf.name in failed:
            log.info("Retry: %s", pdf.name)
            del failed[pdf.name]
        if is_settled(pdf):
            batch.append(pdf)
    return batch


def is_settled(pdf: Path) -> bool:
    """Check if file size is stable across multiple polls."""
    try:
        sizes = []
        for _ in range(SETTLE_POLLS):
            if not pdf.exists():
                return False
            sizes.append(pdf.stat().st_size)
            time.sleep(SETTLE_INTERVAL)

        return len(set(sizes)) == 1 and sizes[0] > 0
    except OSError:
        return False
