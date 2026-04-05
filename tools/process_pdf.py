"""Process a single PDF: OCR + classify → sidecars → archive → rebuild."""

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from config import DATA_DIR, ARCHIVE_DIR, OCR_ENGINE, CLASSIFY_MODEL, get_logger
from ocr import ocr_pdf
from classify import category_for
import build_manifest
import build_search_index

log = get_logger("process")


def process(pdf_path: Path) -> Path:
    """Process a single PDF and return the archive path."""
    name = pdf_path.stem
    now = datetime.now(timezone.utc)

    # OCR + classify
    log.info("OCR + classify %s", pdf_path.name)
    ocr_text, meta = ocr_pdf(pdf_path)

    # Year from document date, not processing date
    year = str(meta.get("date", ""))[:4]
    if not year.isdigit():
        year = str(now.year)

    # Determine category
    category = category_for(meta["document_type"])
    target_dir = ARCHIVE_DIR / year / category
    target_dir.mkdir(parents=True, exist_ok=True)

    log.info("  → %s/%s (%s)", year, category, meta["document_type"])

    # Write .md
    md_path = target_dir / f"{name}.md"
    md_path.write_text(ocr_text, encoding="utf-8")

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

    # Move PDF to archive
    pdf_dst = target_dir / pdf_path.name
    shutil.move(str(pdf_path), str(pdf_dst))

    log.info("  → %s", pdf_dst.relative_to(DATA_DIR))
    return pdf_dst


def rebuild():
    """Rebuild manifests and search index."""
    log.info("Rebuilding manifests...")
    build_manifest.main()
    log.info("Rebuilding search index...")
    build_search_index.main()


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pdf_path> [pdf_path ...]")
        sys.exit(1)

    for arg in sys.argv[1:]:
        pdf_path = Path(arg)
        if not pdf_path.exists():
            log.warning("SKIP %s (not found)", arg)
            continue
        if pdf_path.suffix.lower() != ".pdf":
            log.warning("SKIP %s (not a PDF)", arg)
            continue

        try:
            process(pdf_path)
        except Exception:
            log.exception("Failed to process %s", pdf_path.name)

    # Rebuild once at the end, not after each PDF
    rebuild()


if __name__ == "__main__":
    main()
