"""Build manifest-YYYY.json files from .meta.yml sidecars in the archive."""

import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from config import DATA_DIR, ARCHIVE_DIR, get_logger

log = get_logger("manifest")


def collect_entries(archive_dir: Path) -> tuple[dict[str, list[dict]], int]:
    """Scan archive for .meta.yml files and return entries grouped by year.

    Returns (entries_by_year, error_count).
    """
    entries_by_year: dict[str, list[dict]] = defaultdict(list)
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

        rel = meta_path.relative_to(archive_dir)
        doc_path = str(rel).removesuffix(".meta.yml")
        year = str(rel.parts[0])

        entries_by_year[year].append(
            {
                "path": doc_path,
                "title": meta.get("title", doc_path),
                "date": str(meta.get("date", "")),
                "kind": meta.get("kind", "unknown"),
                "category": meta.get("category", "Sonstiges"),
                "tags": meta.get("tags", []),
            }
        )

    return dict(entries_by_year), errors


def write_manifests(entries_by_year: dict[str, list[dict]], data_dir: Path) -> list[str]:
    """Write manifest-YYYY.json files and manifest-index.json. Returns list of years."""
    years = []
    for year, entries in sorted(entries_by_year.items()):
        entries.sort(key=lambda e: e["date"], reverse=True)
        manifest_path = data_dir / f"manifest-{year}.json"
        manifest_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        years.append(year)
        log.info("manifest-%s.json: %d entries", year, len(entries))

    index_path = data_dir / "manifest-index.json"
    index_path.write_text(
        json.dumps(sorted(years, reverse=True), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return years


def main() -> int:
    """Build manifests. Returns 0 on success, 1 if any files were skipped."""
    if not ARCHIVE_DIR.exists():
        log.warning("Archive directory does not exist: %s", ARCHIVE_DIR)
        return 1

    entries, errors = collect_entries(ARCHIVE_DIR)
    write_manifests(entries, DATA_DIR)

    if errors:
        log.warning("%d files skipped due to errors", errors)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
