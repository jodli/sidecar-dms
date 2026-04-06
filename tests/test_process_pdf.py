"""Tests for process_pdf.py: filename dedup, PDF processing pipeline."""

from unittest.mock import patch

import yaml
import pytest

from process_pdf import unique_stem, process


class TestUniqueStem:
    def test_no_conflict(self, tmp_path):
        assert unique_stem(tmp_path, "document") == "document"

    def test_first_conflict_appends_2(self, tmp_path):
        (tmp_path / "document.meta.yml").touch()
        assert unique_stem(tmp_path, "document") == "document_2"

    def test_multiple_conflicts_increment(self, tmp_path):
        (tmp_path / "document.meta.yml").touch()
        (tmp_path / "document_2.meta.yml").touch()
        (tmp_path / "document_3.meta.yml").touch()
        assert unique_stem(tmp_path, "document") == "document_4"


class TestProcess:
    """Integration tests for process() with mocked OCR."""

    MOCK_META = {
        "title": "Testrechnung",
        "date": "2024-03-15",
        "kind": "rechnung",
        "category": "Rechnungen",
        "sender": "Test GmbH",
        "summary": "Eine Testrechnung",
        "tags": ["test"],
        "fields": {"betrag": "99,00 €"},
    }

    @patch("process_pdf.ocr_pdf")
    def test_creates_sidecar_files(self, mock_ocr, data_dir, archive_dir):
        mock_ocr.return_value = ("OCR Text hier", self.MOCK_META.copy())

        pdf = data_dir / "intake" / "test.pdf"
        pdf.write_bytes(b"%PDF-fake")

        result = process(pdf, archive_dir=archive_dir)

        # PDF moved to archive
        assert not pdf.exists()
        assert result.exists()
        assert result.suffix == ".pdf"

        # Sidecar files created in correct directory
        target_dir = archive_dir / "2024" / "Rechnungen"
        assert (target_dir / "test.md").read_text() == "OCR Text hier"

        meta = yaml.safe_load((target_dir / "test.meta.yml").read_text())
        assert meta["title"] == "Testrechnung"
        assert meta["category"] == "Rechnungen"
        assert "processing" in meta
        assert meta["processing"]["ocr_engine"]
        assert meta["processing"]["processed_at"]

    @patch("process_pdf.ocr_pdf")
    def test_deduplicates_filename(self, mock_ocr, data_dir, archive_dir):
        mock_ocr.return_value = ("OCR Text", self.MOCK_META.copy())

        # Pre-create conflicting file
        target_dir = archive_dir / "2024" / "Rechnungen"
        target_dir.mkdir(parents=True)
        (target_dir / "test.meta.yml").touch()

        pdf = data_dir / "intake" / "test.pdf"
        pdf.write_bytes(b"%PDF-fake")

        result = process(pdf, archive_dir=archive_dir)

        assert result.stem == "test_2"
        assert (target_dir / "test_2.md").exists()
        assert (target_dir / "test_2.meta.yml").exists()

    @patch("process_pdf.ocr_pdf")
    def test_directory_structure_from_metadata(self, mock_ocr, data_dir, archive_dir):
        """Year and category from OCR metadata determine archive path."""
        meta = self.MOCK_META.copy()
        meta["date"] = "2023-07-20"
        meta["category"] = "Steuern"
        mock_ocr.return_value = ("text", meta)

        pdf = data_dir / "intake" / "bescheid.pdf"
        pdf.write_bytes(b"%PDF-fake")

        result = process(pdf, archive_dir=archive_dir)

        assert "2023" in str(result)
        assert "Steuern" in str(result)
