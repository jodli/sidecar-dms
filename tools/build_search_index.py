#!/usr/bin/env python3
"""Build Pagefind search index from .meta.yml + .md sidecars in the archive."""

import asyncio
import os
from pathlib import Path

import yaml
from pagefind.index import PagefindIndex, IndexConfig

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("SIDECAR_DATA_DIR", REPO_ROOT.parent / "sidecar-data"))
ARCHIVE_DIR = DATA_DIR / "archive"
OUTPUT_DIR = DATA_DIR / "pagefind"


async def build():
    print(f"Archive: {ARCHIVE_DIR}")
    print(f"Output:  {OUTPUT_DIR}")

    config = IndexConfig(
        output_path=str(OUTPUT_DIR),
        force_language="de",
    )

    count = 0
    async with PagefindIndex(config=config) as index:
        for meta_path in sorted(ARCHIVE_DIR.rglob("*.meta.yml")):
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))

            # Find corresponding .md file
            md_path = meta_path.with_name(meta_path.name.removesuffix(".meta.yml") + ".md")
            if not md_path.exists():
                print(f"  SKIP {meta_path} (no .md)")
                continue

            ocr_text = md_path.read_text(encoding="utf-8")
            rel_path = str(meta_path.relative_to(ARCHIVE_DIR)).removesuffix(".meta.yml")

            # Combine OCR text with metadata so all fields are searchable
            meta_text = " ".join(filter(None, [
                meta.get("title", ""),
                meta.get("document_type", ""),
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
                    "document_type": [meta.get("document_type", "unknown")],
                },
            )
            count += 1

    print(f"  Indexed {count} documents")
    print("Done.")


def main():
    asyncio.run(build())


if __name__ == "__main__":
    main()
