"""Watch intake folder for new PDFs and process them automatically."""

import time
from pathlib import Path

from config import INTAKE_DIR, get_logger
from process_pdf import process, rebuild

log = get_logger("watch")

POLL_INTERVAL = 2   # seconds
SETTLE_POLLS = 3    # number of stable size checks before processing
SETTLE_INTERVAL = 1 # seconds between settle checks
RETRY_AFTER = 300   # seconds before retrying a failed file


def watch():
    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Watching %s (poll %ds, settle %d×%ds)", INTAKE_DIR, POLL_INTERVAL, SETTLE_POLLS, SETTLE_INTERVAL)

    failed: dict[str, float] = {}  # filename → timestamp of last failure

    while True:
        try:
            pdfs = sorted(INTAKE_DIR.glob("*.pdf"))
            now = time.time()

            for pdf in pdfs:
                # Skip recently failed files
                if pdf.name in failed:
                    if now - failed[pdf.name] < RETRY_AFTER:
                        continue
                    log.info("Retrying %s", pdf.name)
                    del failed[pdf.name]

                # Settle check: file size must be stable across multiple polls
                if not _is_settled(pdf):
                    continue

                log.info("New: %s", pdf.name)
                try:
                    process(pdf)
                    rebuild()
                except Exception:
                    log.exception("Failed to process %s", pdf.name)
                    failed[pdf.name] = time.time()

        except KeyboardInterrupt:
            log.info("Stopped.")
            break
        except Exception:
            log.exception("Watch loop error")

        time.sleep(POLL_INTERVAL)


def _is_settled(pdf: Path) -> bool:
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
