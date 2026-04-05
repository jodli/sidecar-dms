"""Migrate .meta.yml files from v1 (document_type) to v2 (kind + category) schema."""

import shutil
from pathlib import Path

import yaml

from config import ARCHIVE_DIR, get_logger

log = get_logger("migrate")

# Map old folder names to new categories
FOLDER_TO_CATEGORY = {
    "Rechnungen": "Rechnungen",
    "Verträge": "Verträge",
    "Versicherung": "Versicherung",
    "Steuern": "Steuern",
    "Medizin": "Gesundheit",
    "Urkunden": "Behörden",
    "Briefe": "Behörden",
    "Sonstiges": "Sonstiges",
    "Unsortiert": "Sonstiges",
}


def migrate():
    if not ARCHIVE_DIR.exists():
        log.warning("Archive directory does not exist: %s", ARCHIVE_DIR)
        return

    migrated = 0
    skipped = 0

    for meta_path in sorted(ARCHIVE_DIR.rglob("*.meta.yml")):
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
        if not meta or not isinstance(meta, dict):
            log.warning("SKIP %s (ungültiges YAML)", meta_path)
            skipped += 1
            continue

        if "kind" in meta and "category" in meta:
            log.info("SKIP %s (bereits migriert)", meta_path.relative_to(ARCHIVE_DIR))
            skipped += 1
            continue

        old_type = meta.pop("document_type", "unbekannt")
        meta["kind"] = old_type

        # Derive category from folder name
        rel = meta_path.relative_to(ARCHIVE_DIR)
        folder = rel.parts[1] if len(rel.parts) >= 2 else "Sonstiges"
        new_category = FOLDER_TO_CATEGORY.get(folder, "Sonstiges")
        meta["category"] = new_category

        # Move to new folder if category changed
        if folder != new_category:
            stem = meta_path.name.removesuffix(".meta.yml")
            year = rel.parts[0]
            new_dir = ARCHIVE_DIR / year / new_category
            new_dir.mkdir(parents=True, exist_ok=True)

            for suffix in [".meta.yml", ".md", ".pdf"]:
                old = meta_path.parent / f"{stem}{suffix}"
                if old.exists():
                    shutil.move(str(old), str(new_dir / old.name))
                    log.info("  MOVE %s → %s/", old.name, new_category)

            meta_path = new_dir / f"{stem}.meta.yml"

        # Rewrite with updated field order
        ordered = {}
        for key in ["title", "date", "kind", "category", "tags", "sender", "summary", "fields", "processing"]:
            if key in meta:
                ordered[key] = meta[key]
        for key in meta:
            if key not in ordered:
                ordered[key] = meta[key]

        meta_path.write_text(
            yaml.dump(ordered, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        log.info("OK %s (kind=%s, category=%s)", meta_path.relative_to(ARCHIVE_DIR), old_type, new_category)
        migrated += 1

    log.info("Migration fertig: %d migriert, %d übersprungen", migrated, skipped)


if __name__ == "__main__":
    migrate()
