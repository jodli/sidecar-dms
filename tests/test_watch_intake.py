"""Tests for watch_intake.py: batch collection and file settling."""

import time
from unittest.mock import patch

import pytest

from watch_intake import collect_batch, is_settled


class TestCollectBatch:
    def test_empty_intake(self, intake_dir):
        batch = collect_batch(intake_dir, failed={})
        assert batch == []

    def test_collects_settled_pdfs(self, intake_dir):
        pdf = intake_dir / "doc.pdf"
        pdf.write_bytes(b"%PDF-content")

        with patch("watch_intake.is_settled", return_value=True):
            batch = collect_batch(intake_dir, failed={})
        assert len(batch) == 1
        assert batch[0].name == "doc.pdf"

    def test_skips_recently_failed(self, intake_dir):
        pdf = intake_dir / "failed.pdf"
        pdf.write_bytes(b"%PDF-content")

        failed = {"failed.pdf": time.time()}  # failed just now
        with patch("watch_intake.is_settled", return_value=True):
            batch = collect_batch(intake_dir, failed=failed)
        assert batch == []

    def test_retries_after_timeout(self, intake_dir):
        pdf = intake_dir / "retry.pdf"
        pdf.write_bytes(b"%PDF-content")

        failed = {"retry.pdf": time.time() - 400}  # failed 400s ago, RETRY_AFTER=300
        with patch("watch_intake.is_settled", return_value=True):
            batch = collect_batch(intake_dir, failed=failed)
        assert len(batch) == 1
        assert "retry.pdf" not in failed  # cleared from failed dict

    def test_skips_unsettled_files(self, intake_dir):
        pdf = intake_dir / "uploading.pdf"
        pdf.write_bytes(b"%PDF-partial")

        with patch("watch_intake.is_settled", return_value=False):
            batch = collect_batch(intake_dir, failed={})
        assert batch == []

    def test_ignores_non_pdf_files(self, intake_dir):
        (intake_dir / "notes.txt").write_text("hello")
        (intake_dir / "image.png").write_bytes(b"\x89PNG")

        with patch("watch_intake.is_settled", return_value=True):
            batch = collect_batch(intake_dir, failed={})
        assert batch == []


class TestIsSettled:
    def test_stable_file_is_settled(self, tmp_path):
        pdf = tmp_path / "stable.pdf"
        pdf.write_bytes(b"%PDF-1.4 content here")

        with patch("watch_intake.SETTLE_INTERVAL", 0):  # no sleep
            assert is_settled(pdf) is True

    def test_empty_file_not_settled(self, tmp_path):
        pdf = tmp_path / "empty.pdf"
        pdf.write_bytes(b"")

        with patch("watch_intake.SETTLE_INTERVAL", 0):
            assert is_settled(pdf) is False

    def test_deleted_file_not_settled(self, tmp_path):
        pdf = tmp_path / "gone.pdf"
        # file doesn't exist
        with patch("watch_intake.SETTLE_INTERVAL", 0):
            assert is_settled(pdf) is False
