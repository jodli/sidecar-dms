"""Tests for build_search_index.py: document collection for search indexing."""

import yaml

from build_search_index import collect_documents


def _write_sidecar(archive_dir, year, category, stem, meta, ocr_text=None):
    """Write .meta.yml and optionally .md sidecar files."""
    d = archive_dir / year / category
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.meta.yml").write_text(
        yaml.dump(meta, allow_unicode=True), encoding="utf-8"
    )
    if ocr_text is not None:
        (d / f"{stem}.md").write_text(ocr_text, encoding="utf-8")


class TestCollectDocuments:
    def test_empty_archive(self, archive_dir):
        docs, errors = collect_documents(archive_dir)
        assert docs == []
        assert errors == 0

    def test_complete_sidecar_pair(self, archive_dir):
        _write_sidecar(archive_dir, "2024", "Rechnungen", "hornbach",
            meta={"title": "Hornbach", "kind": "rechnung", "sender": "Hornbach",
                  "summary": "Einkauf", "tags": ["baumarkt"], "category": "Rechnungen",
                  "fields": {"betrag": "42,00 €"}},
            ocr_text="Rechnung über Schrauben")

        docs, errors = collect_documents(archive_dir)
        assert len(docs) == 1
        assert errors == 0

        doc = docs[0]
        assert doc["url"] == "2024/Rechnungen/hornbach"
        assert "Hornbach" in doc["content"]
        assert "Rechnung über Schrauben" in doc["content"]
        assert "42,00 €" in doc["content"]
        assert doc["meta"]["title"] == "Hornbach"
        assert doc["filters"]["kind"] == ["rechnung"]
        assert doc["filters"]["category"] == ["Rechnungen"]
        assert "baumarkt" in doc["filters"]["tags"]

    def test_missing_md_skipped(self, archive_dir):
        """meta.yml without .md file is skipped."""
        _write_sidecar(archive_dir, "2024", "Rechnungen", "no-ocr",
            meta={"title": "Ohne OCR", "kind": "rechnung", "category": "Rechnungen"},
            ocr_text=None)

        docs, errors = collect_documents(archive_dir)
        assert docs == []
        assert errors == 1

    def test_invalid_yaml_skipped(self, archive_dir):
        d = archive_dir / "2024" / "Rechnungen"
        d.mkdir(parents=True)
        (d / "broken.meta.yml").write_text(": [invalid", encoding="utf-8")
        (d / "broken.md").write_text("text", encoding="utf-8")

        docs, errors = collect_documents(archive_dir)
        assert docs == []
        assert errors == 1

    def test_mixed_valid_and_invalid(self, archive_dir):
        _write_sidecar(archive_dir, "2024", "Rechnungen", "good",
            meta={"title": "Gut", "kind": "rechnung", "category": "Rechnungen"},
            ocr_text="OCR text")
        _write_sidecar(archive_dir, "2024", "Rechnungen", "no-md",
            meta={"title": "Kein MD", "kind": "rechnung", "category": "Rechnungen"},
            ocr_text=None)

        docs, errors = collect_documents(archive_dir)
        assert len(docs) == 1
        assert docs[0]["meta"]["title"] == "Gut"
        assert errors == 1

    def test_meta_fields_in_content(self, archive_dir):
        """All metadata fields (title, kind, sender, summary, tags, field values) appear in content."""
        _write_sidecar(archive_dir, "2024", "Steuern", "bescheid",
            meta={"title": "Steuerbescheid", "kind": "steuerbescheid",
                  "sender": "Finanzamt", "summary": "Bescheid für 2023",
                  "tags": ["steuer", "2023"], "category": "Steuern",
                  "fields": {"aktenzeichen": "123/456"}},
            ocr_text="Sehr geehrter Steuerzahler")

        docs, _ = collect_documents(archive_dir)
        content = docs[0]["content"]
        assert "Steuerbescheid" in content
        assert "steuerbescheid" in content
        assert "Finanzamt" in content
        assert "Bescheid für 2023" in content
        assert "steuer" in content
        assert "123/456" in content
        assert "Sehr geehrter Steuerzahler" in content
