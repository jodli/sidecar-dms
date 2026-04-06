"""Tests for classify.py: parse_llm_response and validate_metadata."""

import pytest

from classify import ClassificationError, parse_llm_response, validate_metadata, CATEGORIES


# --- parse_llm_response ---


class TestParseLlmResponse:
    def test_direct_json(self):
        raw = '{"title": "Test", "date": "2024-01-01"}'
        assert parse_llm_response(raw) == {"title": "Test", "date": "2024-01-01"}

    def test_markdown_code_block(self):
        raw = '```json\n{"title": "Test"}\n```'
        assert parse_llm_response(raw) == {"title": "Test"}

    def test_markdown_code_block_no_lang(self):
        raw = '```\n{"title": "Test"}\n```'
        assert parse_llm_response(raw) == {"title": "Test"}

    def test_json_embedded_in_text(self):
        raw = 'Hier ist das Ergebnis:\n{"title": "Test"}\nFertig.'
        assert parse_llm_response(raw) == {"title": "Test"}

    def test_garbage_returns_none(self):
        assert parse_llm_response("kein json hier") is None

    def test_empty_string_returns_none(self):
        assert parse_llm_response("") is None

    def test_whitespace_around_json(self):
        raw = '  \n  {"title": "Test"}  \n  '
        assert parse_llm_response(raw) == {"title": "Test"}

    def test_nested_json(self):
        raw = '{"title": "Test", "fields": {"betrag": "123,45 €"}}'
        result = parse_llm_response(raw)
        assert result["fields"]["betrag"] == "123,45 €"


# --- validate_metadata ---


def _valid_raw(**overrides):
    """Return a minimal valid metadata dict, with optional overrides."""
    base = {
        "title": "Testdokument",
        "date": "2024-03-15",
        "kind": "rechnung",
        "category": "Rechnungen",
        "tags": ["test"],
        "sender": "Firma GmbH",
        "summary": "Ein Test.",
        "fields": {"betrag": "42,00 €"},
    }
    base.update(overrides)
    return base


class TestValidateMetadata:
    def test_valid_minimal(self):
        result = validate_metadata(_valid_raw())
        assert result["title"] == "Testdokument"
        assert result["date"] == "2024-03-15"
        assert result["kind"] == "rechnung"
        assert result["category"] == "Rechnungen"

    def test_all_categories_accepted(self):
        for cat in CATEGORIES:
            result = validate_metadata(_valid_raw(category=cat))
            assert result["category"] == cat

    def test_missing_title_raises(self):
        with pytest.raises(ClassificationError, match="title"):
            validate_metadata(_valid_raw(title=""))

    def test_missing_kind_raises(self):
        with pytest.raises(ClassificationError, match="kind"):
            validate_metadata(_valid_raw(kind=""))

    def test_missing_category_raises(self):
        with pytest.raises(ClassificationError, match="category"):
            validate_metadata(_valid_raw(category=""))

    def test_multiple_missing_fields(self):
        with pytest.raises(ClassificationError, match="title.*kind"):
            validate_metadata(_valid_raw(title="", kind=""))

    def test_invalid_category_raises(self):
        with pytest.raises(ClassificationError, match="Ungültige Kategorie"):
            validate_metadata(_valid_raw(category="Fantasie"))

    def test_invalid_date_format_raises(self):
        with pytest.raises(ClassificationError, match="Ungültiges Datum"):
            validate_metadata(_valid_raw(date="15.03.2024"))

    def test_missing_date_raises(self):
        raw = _valid_raw()
        del raw["date"]
        with pytest.raises(ClassificationError, match="Ungültiges Datum"):
            validate_metadata(raw)

    def test_tags_string_converted_to_list(self):
        result = validate_metadata(_valid_raw(tags="einzeltag"))
        assert result["tags"] == ["einzeltag"]

    def test_tags_default_empty_list(self):
        raw = _valid_raw()
        del raw["tags"]
        result = validate_metadata(raw)
        assert result["tags"] == []

    def test_fields_non_dict_becomes_empty(self):
        result = validate_metadata(_valid_raw(fields="kein dict"))
        assert result["fields"] == {}

    def test_fields_default_empty_dict(self):
        raw = _valid_raw()
        del raw["fields"]
        result = validate_metadata(raw)
        assert result["fields"] == {}

    def test_optional_fields_have_defaults(self):
        raw = {"title": "T", "date": "2024-01-01", "kind": "k", "category": "Sonstiges"}
        result = validate_metadata(raw)
        assert result["sender"] == ""
        assert result["summary"] == ""
        assert result["tags"] == []
        assert result["fields"] == {}
