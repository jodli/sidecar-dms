"""Build manifest-YYYY.json files from .meta.yml sidecars in the archive."""

import json
from collections import defaultdict

import yaml

from config import DATA_DIR, ARCHIVE_DIR, get_logger

log = get_logger("manifest")


def main():
    entries_by_year: dict[str, list[dict]] = defaultdict(list)

    for meta_path in sorted(ARCHIVE_DIR.rglob("*.meta.yml")):
        try:
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
            if not meta or not isinstance(meta, dict):
                raise ValueError("empty or invalid YAML")
        except Exception:
            log.warning("Skipping %s (invalid YAML)", meta_path.relative_to(ARCHIVE_DIR))
            continue

        rel = meta_path.relative_to(ARCHIVE_DIR)
        doc_path = str(rel).removesuffix(".meta.yml")
        year = str(rel.parts[0])

        entries_by_year[year].append(
            {
                "path": doc_path,
                "title": meta.get("title", doc_path),
                "date": str(meta.get("date", "")),
                "type": meta.get("document_type", "unknown"),
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
        log.info("manifest-%s.json: %d entries", year, len(entries))


if __name__ == "__main__":
    main()
