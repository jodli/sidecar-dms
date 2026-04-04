#!/usr/bin/env python3
"""Watch intake folder for new PDFs and process them automatically."""

import os
import sys
import time
from pathlib import Path

# Load .env from repo root if present
REPO_ROOT = Path(__file__).resolve().parent.parent
_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

DATA_DIR = Path(os.environ.get("SIDECAR_DATA_DIR", REPO_ROOT.parent / "sidecar-data"))
INTAKE_DIR = DATA_DIR / "intake"
POLL_INTERVAL = 2  # seconds
SETTLE_TIME = 1    # seconds — wait for file to finish writing

from process_pdf import process  # noqa: E402


def watch():
    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Watching {INTAKE_DIR}")
    print(f"Poll every {POLL_INTERVAL}s, settle time {SETTLE_TIME}s")
    print()

    seen = set()

    while True:
        try:
            pdfs = sorted(INTAKE_DIR.glob("*.pdf"))
            for pdf in pdfs:
                if pdf.name in seen:
                    continue

                # Wait for file to settle (finish writing)
                size = pdf.stat().st_size
                time.sleep(SETTLE_TIME)
                if not pdf.exists() or pdf.stat().st_size != size:
                    continue

                print(f"New: {pdf.name}")
                try:
                    process(pdf)
                except Exception as e:
                    print(f"  ERROR: {e}", file=sys.stderr)
                    seen.add(pdf.name)  # don't retry failed files

        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Watch error: {e}", file=sys.stderr)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    watch()
