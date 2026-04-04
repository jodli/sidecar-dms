#!/usr/bin/env python3
"""Process a single PDF: OCR + classify → sidecars → archive → rebuild."""

import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Load .env from repo root if present
REPO_ROOT = Path(__file__).resolve().parent.parent
_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

DATA_DIR = Path(os.environ.get("SIDECAR_DATA_DIR", REPO_ROOT.parent / "sidecar-data"))
ARCHIVE_DIR = DATA_DIR / "archive"

from ocr import OCR_ENGINE, ocr_pdf  # noqa: E402
from classify import CLASSIFY_MODEL, category_for  # noqa: E402
import build_manifest  # noqa: E402
import build_search_index  # noqa: E402


def process(pdf_path: Path) -> Path:
    """Process a single PDF and return the archive path."""
    name = pdf_path.stem
    now = datetime.now(timezone.utc)

    # OCR + classify in one request
    print(f"  OCR + classify  {pdf_path.name} ...")
    ocr_text, meta = ocr_pdf(pdf_path)

    # Year from document date, not processing date
    year = str(meta.get("date", ""))[:4]
    if not year.isdigit():
        year = str(now.year)

    # Determine category from document_type
    category = category_for(meta["document_type"])
    target_dir = ARCHIVE_DIR / year / category
    target_dir.mkdir(parents=True, exist_ok=True)

    print(f"  TYPE {meta['document_type']} → {category}")

    # Write .md
    md_path = target_dir / f"{name}.md"
    md_path.write_text(ocr_text, encoding="utf-8")
    print(f"  MD   {md_path.relative_to(DATA_DIR)}")

    # Add processing metadata
    meta["processing"] = {
        "ocr_engine": OCR_ENGINE,
        "classifier": CLASSIFY_MODEL,
        "processed_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "text_layer_embedded": False,
    }

    # Write .meta.yml
    meta_path = target_dir / f"{name}.meta.yml"
    meta_path.write_text(
        yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"  META {meta_path.relative_to(DATA_DIR)}")

    # Move PDF to archive
    pdf_dst = target_dir / pdf_path.name
    shutil.move(str(pdf_path), str(pdf_dst))
    print(f"  PDF  {pdf_dst.relative_to(DATA_DIR)}")

    # Rebuild manifest + search index
    print("  Rebuilding manifests...")
    build_manifest.main()
    print("  Rebuilding search index...")
    build_search_index.main()

    return pdf_dst


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pdf_path> [pdf_path ...]")
        sys.exit(1)

    for arg in sys.argv[1:]:
        pdf_path = Path(arg)
        if not pdf_path.exists():
            print(f"SKIP  {arg} (not found)")
            continue
        if pdf_path.suffix.lower() != ".pdf":
            print(f"SKIP  {arg} (not a PDF)")
            continue

        print(f"Processing {pdf_path.name}")
        try:
            process(pdf_path)
            print(f"  Done.\n")
        except Exception as e:
            print(f"  ERROR: {e}\n", file=sys.stderr)


if __name__ == "__main__":
    main()
