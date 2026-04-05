"""Document classification: prompt, validation, and category mapping."""

import json
import re

CATEGORIES = [
    "Einkommen",
    "Steuern",
    "Finanzen",
    "Versicherung",
    "Wohnen",
    "Gesundheit",
    "Rechnungen",
    "Verträge",
    "Behörden",
    "Sonstiges",
]

SYSTEM_PROMPT = """Du bist ein Dokumenten-Klassifikator. Analysiere das folgende Dokument und extrahiere strukturierte Metadaten.

Antworte NUR mit validem JSON, kein anderer Text davor oder danach.

Schema:
{
  "title": "Kurzer beschreibender Titel auf Deutsch",
  "date": "YYYY-MM-DD (das Datum AUS dem Dokument, nicht das heutige Datum)",
  "kind": "Spezifischer Dokumenttyp auf Deutsch, z.B. rechnung, kassenbon, lohnsteuerbescheinigung, mietvertrag, kontoauszug, rezept, steuerbescheid, gehaltsabrechnung, spendenbescheinigung, versicherungspolice, nebenkostenabrechnung, handwerkerrechnung — oder ein anderer passender Typ",
  "category": "MUSS einer der folgenden sein: Einkommen, Steuern, Finanzen, Versicherung, Wohnen, Gesundheit, Rechnungen, Verträge, Behörden, Sonstiges",
  "tags": ["relevante", "deutsche", "schlagwörter"],
  "sender": "Absender oder Aussteller des Dokuments",
  "summary": "1-2 Sätze Zusammenfassung auf Deutsch",
  "fields": { "dokumenttyp-spezifische Schlüssel-Wert-Paare auf Deutsch, z.B. betrag, währung, vertragsnummer, aktenzeichen, kundennummer" }
}

Hinweise zu category:
- Einkommen: Gehaltsabrechnungen, Lohnsteuerbescheinigungen, Rentenbescheide
- Steuern: Steuerbescheide, Steuererklärungen, Jahressteuerbescheinigungen
- Finanzen: Kontoauszüge, Depotauszüge, Zinsabrechnungen, Riester, Rürup
- Versicherung: Policen, Beitragsbescheinigungen, Schadenmeldungen
- Wohnen: Mietvertrag, Nebenkostenabrechnung, Grundsteuer
- Gesundheit: Arztbriefe, Rezepte, Befunde, Krankenkasse
- Rechnungen: Einkäufe, Handwerker, Dienstleistungen
- Verträge: Mobilfunk, Internet, Strom, Abos
- Behörden: Urkunden, Bescheide, amtliche Schreiben
- Sonstiges: Nur wenn nichts anderes passt"""


class ClassificationError(Exception):
    """Raised when LLM classification output is unusable."""


def validate_metadata(raw: dict) -> dict:
    """Validate LLM-generated metadata. Raises ClassificationError for missing required fields."""
    # Required fields
    title = raw.get("title")
    kind = raw.get("kind")
    category = raw.get("category")

    missing = [k for k, v in [("title", title), ("kind", kind), ("category", category)] if not v]
    if missing:
        raise ClassificationError(f"Pflichtfelder fehlen: {', '.join(missing)}")

    if category not in CATEGORIES:
        raise ClassificationError(f"Ungültige Kategorie: {category!r} (erlaubt: {', '.join(CATEGORIES)})")

    # Validate date format
    date_str = str(raw.get("date", ""))
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ClassificationError(f"Ungültiges Datum: {date_str!r} (erwartet: YYYY-MM-DD)")

    # Optional fields
    tags = raw.get("tags", [])
    if not isinstance(tags, list):
        tags = [str(tags)]
    fields = raw.get("fields", {})
    if not isinstance(fields, dict):
        fields = {}

    return {
        "title": title,
        "date": date_str,
        "kind": kind,
        "category": category,
        "sender": raw.get("sender", ""),
        "summary": raw.get("summary", ""),
        "tags": tags,
        "fields": fields,
    }


def parse_llm_response(text: str) -> dict | None:
    """Try to extract JSON from LLM response text. Returns None on failure."""
    text = text.strip()

    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Markdown code block
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # First { ... } block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None
