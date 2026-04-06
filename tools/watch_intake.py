"""Watch intake folder for new PDFs and process them automatically."""

import signal
import time
from pathlib import Path

from config import DATA_DIR, INTAKE_DIR, get_logger
from process_pdf import process, rebuild

log = get_logger("watch")

POLL_INTERVAL = 2   # seconds
SETTLE_POLLS = 3    # number of stable size checks before processing
SETTLE_INTERVAL = 1 # seconds between settle checks
RETRY_AFTER = 300   # seconds before retrying a failed file
BATCH_WAIT = 3      # extra seconds to wait after a batch for more files

_running = True


def _handle_signal(signum, frame):
    global _running
    log.info("Signal %d received, finishing current batch...", signum)
    _running = False


def watch():
    global _running
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Watching %s (poll %ds, settle %d×%ds)", INTAKE_DIR, POLL_INTERVAL, SETTLE_POLLS, SETTLE_INTERVAL)

    failed: dict[str, float] = {}

    while _running:
        batch = collect_batch(INTAKE_DIR, failed)

        if batch:
            log.info("Batch: %d PDFs", len(batch))
            processed = 0
            for i, pdf in enumerate(batch, 1):
                if not _running:
                    break
                try:
                    result = process(pdf)
                    processed += 1
                    rel = result.relative_to(DATA_DIR) if DATA_DIR in result.parents else result
                    log.info("[%d/%d] %s → %s", i, len(batch), pdf.name, rel)
                except Exception:
                    log.exception("[%d/%d] FEHLER %s", i, len(batch), pdf.name)
                    failed[pdf.name] = time.time()

            if processed and _running:
                time.sleep(BATCH_WAIT)
                extra = collect_batch(INTAKE_DIR, failed)
                if extra:
                    log.info("Weitere %d PDFs gefunden, verarbeite...", len(extra))
                    for i, pdf in enumerate(extra, 1):
                        if not _running:
                            break
                        try:
                            result = process(pdf)
                            processed += 1
                            rel = result.relative_to(DATA_DIR) if DATA_DIR in result.parents else result
                            log.info("[%d/%d] %s → %s", i, len(extra), pdf.name, rel)
                        except Exception:
                            log.exception("[%d/%d] FEHLER %s", i, len(extra), pdf.name)
                            failed[pdf.name] = time.time()

                rebuild()
                log.info("Batch fertig: %d verarbeitet", processed)

        if _running:
            time.sleep(POLL_INTERVAL)

    log.info("Stopped.")


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


if __name__ == "__main__":
    import build_manifest
    import build_search_index

    # Rebuild on startup
    log.info("Rebuilding manifests...")
    build_manifest.main()
    log.info("Rebuilding search index...")
    build_search_index.main()

    watch()
