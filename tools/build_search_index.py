"""Build Pagefind search index from .meta.yml + .md sidecars in the archive."""

import asyncio
import sys
from pathlib import Path

import yaml
from pagefind.index import PagefindIndex, IndexConfig

from config import DATA_DIR, ARCHIVE_DIR, get_logger

log = get_logger("search")

OUTPUT_DIR = DATA_DIR / "pagefind"


def collect_documents(archive_dir: Path) -> tuple[list[dict], int]:
    """Collect indexable documents from archive sidecars.

    Returns (documents, error_count) where each document is a dict with:
    url, content, meta, filters.
    """
    documents = []
    errors = 0

    for meta_path in sorted(archive_dir.rglob("*.meta.yml")):
        try:
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            if not meta or not isinstance(meta, dict):
                raise ValueError("empty or invalid YAML")
        except (yaml.YAMLError, ValueError) as e:
            log.warning("Skipping %s (%s)", meta_path.relative_to(archive_dir), e)
            errors += 1
            continue

        md_path = meta_path.with_name(meta_path.name.removesuffix(".meta.yml") + ".md")
        if not md_path.exists():
            log.warning("Skipping %s (no .md)", meta_path.relative_to(archive_dir))
            errors += 1
            continue

        try:
            ocr_text = md_path.read_text(encoding="utf-8")
        except OSError as e:
            log.warning("Skipping %s (%s)", md_path.relative_to(archive_dir), e)
            errors += 1
            continue

        rel_path = str(meta_path.relative_to(archive_dir)).removesuffix(".meta.yml")

        meta_text = " ".join(filter(None, [
            meta.get("title", ""),
            meta.get("kind", ""),
            meta.get("sender", ""),
            meta.get("summary", ""),
            " ".join(meta.get("tags", [])),
            " ".join(str(v) for v in meta.get("fields", {}).values()),
        ]))

        documents.append({
            "url": rel_path,
            "content": f"{meta_text}\n\n{ocr_text}",
            "meta": {"title": meta.get("title", rel_path)},
            "filters": {
                "tags": meta.get("tags", []),
                "kind": [meta.get("kind", "unknown")],
                "category": [meta.get("category", "Sonstiges")],
            },
        })

    return documents, errors


async def build_index(documents: list[dict], output_dir: Path) -> int:
    """Write Pagefind index from collected documents. Returns count indexed."""
    config = IndexConfig(
        output_path=str(output_dir),
        force_language="de",
    )

    count = 0
    async with PagefindIndex(config=config) as index:
        for doc in documents:
            await index.add_custom_record(
                url=doc["url"],
                content=doc["content"],
                language="de",
                meta=doc["meta"],
                filters=doc["filters"],
            )
            count += 1

    return count


def main() -> int:
    """Build search index. Returns 0 on success, 1 if any files were skipped."""
    if not ARCHIVE_DIR.exists():
        log.warning("Archive directory does not exist: %s", ARCHIVE_DIR)
        return 1

    documents, errors = collect_documents(ARCHIVE_DIR)
    count = asyncio.run(build_index(documents, OUTPUT_DIR))
    log.info("Indexed %d documents", count)

    if errors:
        log.warning("%d files skipped due to errors", errors)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
