#!/usr/bin/env python3
"""Document classification: prompt, validation, and category mapping."""

import json
import os
import re
from datetime import datetime, timezone

CLASSIFY_MODEL = os.environ.get("CLASSIFY_MODEL", "google/gemma-4-31b-it")

SYSTEM_PROMPT = """Du bist ein Dokumenten-Klassifikator. Analysiere den folgenden OCR-Text und extrahiere strukturierte Metadaten.

Antworte NUR mit validem JSON, kein anderer Text davor oder danach.

Schema:
{
  "title": "Kurzer beschreibender Titel auf Deutsch",
  "date": "YYYY-MM-DD (das Datum AUS dem Dokument, nicht das heutige Datum)",
  "document_type": "z.B. rechnung, kassenbon, brief, vertrag, urkunde, steuererklärung, steuerbescheid, medizin, rezept, anleitung, bescheid, versicherung — oder ein anderer passender deutscher Typ",
  "tags": ["relevante", "deutsche", "schlagwörter"],
  "sender": "Absender oder Aussteller des Dokuments",
  "summary": "1-2 Sätze Zusammenfassung auf Deutsch",
  "fields": { "dokumenttyp-spezifische Schlüssel-Wert-Paare auf Deutsch, z.B. betrag, währung, vertragsnummer, aktenzeichen, kundennummer" }
}"""

CATEGORY_MAP = {
    "rechnung": "Rechnungen",
    "kassenbon": "Rechnungen",
    "brief": "Briefe",
    "vertrag": "Verträge",
    "kaufvertrag": "Verträge",
    "versicherung": "Versicherung",
    "urkunde": "Urkunden",
    "steuererklärung": "Steuern",
    "steuerbescheid": "Steuern",
    "anleitung": "Sonstiges",
    "medizin": "Medizin",
    "rezept": "Medizin",
    "bescheid": "Briefe",
}


def category_for(document_type: str) -> str:
    """Map document_type to archive category folder. Falls back to 'Unsortiert'."""
    return CATEGORY_MAP.get(document_type.lower(), "Unsortiert")


def validate_metadata(raw: dict) -> dict:
    """Validate and fill defaults for LLM-generated metadata."""
    meta = {}

    meta["title"] = raw.get("title", "Unbekanntes Dokument")
    meta["document_type"] = raw.get("document_type", "unclassified")
    meta["tags"] = raw.get("tags", [])
    meta["sender"] = raw.get("sender", "")
    meta["summary"] = raw.get("summary", "")
    meta["fields"] = raw.get("fields", {})

    # Validate date format
    date_str = raw.get("date", "")
    if re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_str)):
        meta["date"] = str(date_str)
    else:
        meta["date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Ensure tags is a list
    if not isinstance(meta["tags"], list):
        meta["tags"] = [str(meta["tags"])]

    # Ensure fields is a dict
    if not isinstance(meta["fields"], dict):
        meta["fields"] = {}

    return meta


def parse_llm_response(text: str) -> dict | None:
    """Try to extract JSON from LLM response text. Returns None on failure."""
    text = text.strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


def stub_metadata(name: str = "Unbekannt") -> dict:
    """Return minimal stub metadata for when classification fails."""
    now = datetime.now(timezone.utc)
    return {
        "title": name,
        "date": now.strftime("%Y-%m-%d"),
        "document_type": "unclassified",
        "tags": [],
        "sender": "",
        "summary": "",
        "fields": {},
    }
