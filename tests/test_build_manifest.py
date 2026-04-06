"""Tests for build_manifest.py: manifest generation from .meta.yml sidecars."""

import json

import yaml

from build_manifest import collect_entries, write_manifests


def _write_meta(archive_dir, year, category, stem, meta):
    """Helper: write a .meta.yml file in the archive structure."""
    d = archive_dir / year / category
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{stem}.meta.yml"
    path.write_text(yaml.dump(meta, allow_unicode=True), encoding="utf-8")
    return path


class TestCollectEntries:
    def test_empty_archive(self, archive_dir):
        entries, errors = collect_entries(archive_dir)
        assert entries == {}
        assert errors == 0

    def test_single_document(self, archive_dir):
        _write_meta(archive_dir, "2024", "Rechnungen", "hornbach", {
            "title": "Hornbach Rechnung",
            "date": "2024-03-15",
            "kind": "rechnung",
            "category": "Rechnungen",
            "tags": ["baumarkt"],
        })
        entries, errors = collect_entries(archive_dir)
        assert "2024" in entries
        assert len(entries["2024"]) == 1
        assert entries["2024"][0]["title"] == "Hornbach Rechnung"
        assert entries["2024"][0]["path"] == "2024/Rechnungen/hornbach"

    def test_multiple_years(self, archive_dir):
        _write_meta(archive_dir, "2023", "Steuern", "bescheid", {
            "title": "Steuerbescheid 2023", "date": "2023-06-01",
            "kind": "steuerbescheid", "category": "Steuern",
        })
        _write_meta(archive_dir, "2024", "Rechnungen", "rechnung", {
            "title": "Rechnung 2024", "date": "2024-01-10",
            "kind": "rechnung", "category": "Rechnungen",
        })
        entries, _ = collect_entries(archive_dir)
        assert set(entries.keys()) == {"2023", "2024"}

    def test_invalid_yaml_counted_as_error(self, archive_dir):
        d = archive_dir / "2024" / "Rechnungen"
        d.mkdir(parents=True)
        (d / "broken.meta.yml").write_text(": invalid: yaml: [", encoding="utf-8")

        entries, errors = collect_entries(archive_dir)
        assert entries == {}
        assert errors == 1

    def test_empty_yaml_counted_as_error(self, archive_dir):
        d = archive_dir / "2024" / "Rechnungen"
        d.mkdir(parents=True)
        (d / "empty.meta.yml").write_text("", encoding="utf-8")

        entries, errors = collect_entries(archive_dir)
        assert entries == {}
        assert errors == 1

    def test_missing_optional_fields_get_defaults(self, archive_dir):
        _write_meta(archive_dir, "2024", "Sonstiges", "minimal", {
            "title": "Nur Titel",
            "date": "2024-01-01",
        })
        entries, _ = collect_entries(archive_dir)
        entry = entries["2024"][0]
        assert entry["kind"] == "unknown"
        assert entry["category"] == "Sonstiges"
        assert entry["tags"] == []

    def test_valid_and_invalid_mixed(self, archive_dir):
        """Valid files are collected, invalid ones counted as errors."""
        _write_meta(archive_dir, "2024", "Rechnungen", "good", {
            "title": "Gute Rechnung", "date": "2024-05-01",
            "kind": "rechnung", "category": "Rechnungen",
        })
        d = archive_dir / "2024" / "Rechnungen"
        (d / "bad.meta.yml").write_text("not: [valid", encoding="utf-8")

        entries, errors = collect_entries(archive_dir)
        assert len(entries["2024"]) == 1
        assert errors == 1


class TestWriteManifests:
    def test_writes_manifest_and_index(self, data_dir):
        entries = {
            "2024": [
                {"path": "2024/Rechnungen/a", "title": "A", "date": "2024-06-01",
                 "kind": "rechnung", "category": "Rechnungen", "tags": []},
                {"path": "2024/Rechnungen/b", "title": "B", "date": "2024-01-15",
                 "kind": "rechnung", "category": "Rechnungen", "tags": []},
            ]
        }
        write_manifests(entries, data_dir)

        manifest = json.loads((data_dir / "manifest-2024.json").read_text())
        assert len(manifest) == 2
        # Sorted by date descending
        assert manifest[0]["date"] == "2024-06-01"
        assert manifest[1]["date"] == "2024-01-15"

        index = json.loads((data_dir / "manifest-index.json").read_text())
        assert index == ["2024"]

    def test_multiple_years_in_index(self, data_dir):
        entries = {
            "2023": [{"path": "p", "title": "T", "date": "2023-01-01",
                       "kind": "k", "category": "c", "tags": []}],
            "2024": [{"path": "p", "title": "T", "date": "2024-01-01",
                       "kind": "k", "category": "c", "tags": []}],
        }
        write_manifests(entries, data_dir)

        index = json.loads((data_dir / "manifest-index.json").read_text())
        assert index == ["2024", "2023"]  # descending

    def test_empty_entries_writes_empty_index(self, data_dir):
        write_manifests({}, data_dir)
        index = json.loads((data_dir / "manifest-index.json").read_text())
        assert index == []
