"""Build Pagefind search index from .meta.yml + .md sidecars in the archive."""

import asyncio

import yaml
from pagefind.index import PagefindIndex, IndexConfig

from config import DATA_DIR, ARCHIVE_DIR, get_logger

log = get_logger("search")

OUTPUT_DIR = DATA_DIR / "pagefind"


async def build():
    if not ARCHIVE_DIR.exists():
        log.warning("Archive directory does not exist: %s", ARCHIVE_DIR)
        return

    config = IndexConfig(
        output_path=str(OUTPUT_DIR),
        force_language="de",
    )

    count = 0
    async with PagefindIndex(config=config) as index:
        for meta_path in sorted(ARCHIVE_DIR.rglob("*.meta.yml")):
            try:
                meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
                if not meta or not isinstance(meta, dict):
                    raise ValueError("empty or invalid YAML")
            except Exception:
                log.warning("Skipping %s (invalid YAML)", meta_path.relative_to(ARCHIVE_DIR))
                continue

            md_path = meta_path.with_name(meta_path.name.removesuffix(".meta.yml") + ".md")
            if not md_path.exists():
                log.warning("Skipping %s (no .md)", meta_path.relative_to(ARCHIVE_DIR))
                continue

            try:
                ocr_text = md_path.read_text(encoding="utf-8")
            except Exception:
                log.warning("Skipping %s (unreadable .md)", md_path.relative_to(ARCHIVE_DIR))
                continue

            rel_path = str(meta_path.relative_to(ARCHIVE_DIR)).removesuffix(".meta.yml")

            meta_text = " ".join(filter(None, [
                meta.get("title", ""),
                meta.get("kind", ""),
                meta.get("sender", ""),
                meta.get("summary", ""),
                " ".join(meta.get("tags", [])),
                " ".join(str(v) for v in meta.get("fields", {}).values()),
            ]))
            content = f"{meta_text}\n\n{ocr_text}"

            await index.add_custom_record(
                url=rel_path,
                content=content,
                language="de",
                meta={"title": meta.get("title", rel_path)},
                filters={
                    "tags": meta.get("tags", []),
                    "kind": [meta.get("kind", "unknown")],
                    "category": [meta.get("category", "Sonstiges")],
                },
            )
            count += 1

    log.info("Indexed %d documents", count)


def main():
    asyncio.run(build())


if __name__ == "__main__":
    main()
