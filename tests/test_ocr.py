"""Tests for ocr.py: annotation extraction and retry logic."""

from unittest.mock import patch, MagicMock

import pytest
import requests

from ocr import _extract_ocr_text, _request_with_retry


class TestExtractOcrText:
    def test_single_text_annotation(self):
        annotations = [{
            "type": "file",
            "file": {
                "content": [{"type": "text", "text": "Rechnung vom 15.03.2024"}]
            }
        }]
        assert _extract_ocr_text(annotations) == "Rechnung vom 15.03.2024"

    def test_multiple_pages(self):
        annotations = [{
            "type": "file",
            "file": {
                "content": [
                    {"type": "text", "text": "Seite 1"},
                    {"type": "text", "text": "Seite 2"},
                ]
            }
        }]
        result = _extract_ocr_text(annotations)
        assert "Seite 1" in result
        assert "Seite 2" in result

    def test_strips_file_xml_tags(self):
        annotations = [{
            "type": "file",
            "file": {
                "content": [{"type": "text", "text": '<file name="doc.pdf">\nInhalt\n</file>'}]
            }
        }]
        assert _extract_ocr_text(annotations) == "Inhalt"

    def test_empty_annotations(self):
        assert _extract_ocr_text([]) == ""

    def test_non_file_annotations_ignored(self):
        annotations = [{"type": "url_citation", "url": "http://example.com"}]
        assert _extract_ocr_text(annotations) == ""

    def test_empty_text_parts_skipped(self):
        annotations = [{
            "type": "file",
            "file": {
                "content": [
                    {"type": "text", "text": ""},
                    {"type": "text", "text": "Echte Daten"},
                ]
            }
        }]
        assert _extract_ocr_text(annotations) == "Echte Daten"


class TestRequestWithRetry:
    def _mock_response(self, status_code=200, json_data=None):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.text = "{}"
        resp.raise_for_status = MagicMock()
        if status_code >= 400:
            resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
        return resp

    @patch("ocr.time.sleep")  # don't actually sleep in tests
    @patch("ocr.requests.post")
    def test_success_on_first_try(self, mock_post, mock_sleep):
        mock_post.return_value = self._mock_response(200, {"choices": []})
        result = _request_with_retry({"model": "test"})
        assert result == {"choices": []}
        assert mock_post.call_count == 1

    @patch("ocr.time.sleep")
    @patch("ocr.requests.post")
    def test_retries_on_429(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            self._mock_response(429),
            self._mock_response(200, {"choices": []}),
        ]
        result = _request_with_retry({"model": "test"})
        assert result == {"choices": []}
        assert mock_post.call_count == 2

    @patch("ocr.time.sleep")
    @patch("ocr.requests.post")
    def test_retries_on_500(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            self._mock_response(500),
            self._mock_response(200, {"choices": []}),
        ]
        result = _request_with_retry({"model": "test"})
        assert mock_post.call_count == 2

    @patch("ocr.time.sleep")
    @patch("ocr.requests.post")
    def test_raises_after_max_retries(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            self._mock_response(429),
            self._mock_response(429),
            self._mock_response(429),
        ]
        with pytest.raises(requests.HTTPError):
            _request_with_retry({"model": "test"})
        assert mock_post.call_count == 3  # 1 + MAX_RETRIES

    @patch("ocr.time.sleep")
    @patch("ocr.requests.post")
    def test_retries_on_connection_error(self, mock_post, mock_sleep):
        mock_post.side_effect = [
            requests.ConnectionError("connection reset"),
            self._mock_response(200, {"choices": []}),
        ]
        result = _request_with_retry({"model": "test"})
        assert result == {"choices": []}

    @patch("ocr.time.sleep")
    @patch("ocr.requests.post")
    def test_raises_after_persistent_connection_error(self, mock_post, mock_sleep):
        mock_post.side_effect = requests.ConnectionError("down")
        with pytest.raises(RuntimeError, match="unreachable"):
            _request_with_retry({"model": "test"})
