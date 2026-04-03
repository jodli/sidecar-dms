#!/usr/bin/env python3
"""Build manifest-YYYY.json files from .meta.yml sidecars in the archive."""

import json
import os
from collections import defaultdict
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("SIDECAR_DATA_DIR", REPO_ROOT.parent / "sidecar-data"))
ARCHIVE_DIR = DATA_DIR / "archive"


def main():
    print(f"Archive: {ARCHIVE_DIR}")

    entries_by_year: dict[str, list[dict]] = defaultdict(list)

    for meta_path in sorted(ARCHIVE_DIR.rglob("*.meta.yml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))

        # path relative to archive/, without .meta.yml extension
        rel = meta_path.relative_to(ARCHIVE_DIR)
        doc_path = str(rel).removesuffix(".meta.yml")

        year = str(rel.parts[0])

        entries_by_year[year].append(
            {
                "path": doc_path,
                "title": meta["title"],
                "date": str(meta["date"]),
                "type": meta["document_type"],
                "tags": meta.get("tags", []),
            }
        )

    for year, entries in sorted(entries_by_year.items()):
        entries.sort(key=lambda e: e["date"], reverse=True)
        manifest_path = DATA_DIR / f"manifest-{year}.json"
        manifest_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  {manifest_path.name}: {len(entries)} entries")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
