#!/usr/bin/env python3
"""One-time import: convert existing md/ + pdf/ into archive structure with .meta.yml sidecars."""

import os
import re
import shutil
from pathlib import Path

import yaml

# Source directories (relative to repo root)
REPO_ROOT = Path(__file__).resolve().parent.parent
MD_DIR = REPO_ROOT / "md"
PDF_DIR = REPO_ROOT / "pdf"

# Data directory
DATA_DIR = Path(os.environ.get("SIDECAR_DATA_DIR", REPO_ROOT.parent / "sidecar-data"))
ARCHIVE_DIR = DATA_DIR / "archive"

# Document metadata — hardcoded with realistic values
DOCUMENTS = {
    "20251009-1034": {
        "category": "Steuern",
        "meta": {
            "title": "Fragebogen zur Steuererklärung — Häusliches Arbeitszimmer",
            "date": "2025-09-15",
            "document_type": "tax_form",
            "tags": ["steuern", "arbeitszimmer", "finanzamt"],
            "sender": "Finanzamt Hersbruck",
            "summary": "Fragebogen zur steuerlichen Geltendmachung eines häuslichen Arbeitszimmers für das Steuerjahr 2024.",
            "fields": {
                "tax_year": 2024,
                "tax_office": "Finanzamt Hersbruck",
                "reference_number": "217/123/45678",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "20251009-1605": {
        "category": "Steuern",
        "meta": {
            "title": "Einkommensteuerbescheid 2024",
            "date": "2025-10-09",
            "document_type": "tax_assessment",
            "tags": ["steuern", "einkommensteuer", "solidaritätszuschlag"],
            "sender": "Finanzamt Hersbruck",
            "summary": "Einkommensteuerbescheid für 2024. Festgesetzte Steuer 4.832 EUR, Erstattung 1.247,38 EUR.",
            "fields": {
                "tax_year": 2024,
                "assessed_tax": 4832.00,
                "refund": 1247.38,
                "currency": "EUR",
                "tax_office": "Finanzamt Hersbruck",
                "reference_number": "217/123/45678",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "20251009_Canada_life": {
        "category": "Versicherung",
        "meta": {
            "title": "Canada Life — Vertragsanpassung Beitragserhöhung",
            "date": "2025-10-01",
            "document_type": "contract",
            "tags": ["versicherung", "canada-life", "lebensversicherung"],
            "sender": "Canada Life Assurance Europe plc",
            "summary": "Mitteilung über planmäßige Beitragserhöhung der fondsgebundenen Lebensversicherung ab 01.01.2026.",
            "fields": {
                "policy_number": "CL-2019-4472831",
                "new_premium": 185.00,
                "old_premium": 175.00,
                "currency": "EUR",
                "effective_date": "2026-01-01",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "20251010": {
        "category": "Banking",
        "meta": {
            "title": "ING — Eröffnung Direkt-Depot Junior",
            "date": "2025-10-10",
            "document_type": "letter",
            "tags": ["banking", "depot", "ing", "wertpapiere"],
            "sender": "ING-DiBa AG",
            "summary": "Bestätigung der Eröffnung eines Direkt-Depot Junior für Tim Valentin Becker. Depotführung kostenlos.",
            "fields": {
                "depot_number": "5478 2391 00",
                "account_holder": "Tim Valentin Becker",
                "depot_type": "Direkt-Depot Junior",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "20251016-1814": {
        "category": "Rechnungen",
        "meta": {
            "title": "Hornbach Einkauf — Holz und Schrauben",
            "date": "2025-10-16",
            "document_type": "invoice",
            "tags": ["hornbach", "baumarkt", "einkauf"],
            "sender": "HORNBACH Baumarkt Nürnberg",
            "summary": "Kassenbon Hornbach: diverse Holzlatten, Schrauben und Winkel. Gesamtbetrag 87,43 EUR bar bezahlt.",
            "fields": {
                "amount": 87.43,
                "currency": "EUR",
                "payment_method": "bar",
                "items_count": 12,
                "store": "Hornbach Nürnberg-Moorenbrunn",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "Eheurkunde": {
        "category": "Urkunden",
        "meta": {
            "title": "Eheurkunde — Becker / Hoppe",
            "date": "2020-07-18",
            "document_type": "certificate",
            "tags": ["urkunde", "ehe", "standesamt"],
            "sender": "Standesamt Radebeul",
            "summary": "Eheurkunde über die Eheschließung am 18.07.2020. Ehegatten: Jan-Olaf Jürgen Becker und Sindy Hoppe, geb. Hoppe.",
            "fields": {
                "registry_number": "42/2020",
                "registry_office": "Standesamt Radebeul",
                "marriage_date": "2020-07-18",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "Einbenennung_Tim": {
        "category": "Urkunden",
        "meta": {
            "title": "Einbenennung — Tim Valentin Becker",
            "date": "2020-09-14",
            "document_type": "certificate",
            "tags": ["urkunde", "namensänderung", "familienrecht"],
            "sender": "Standesamt Nürnberg",
            "summary": "Einbenennung des Kindes Tim Valentin zum Ehenamen Becker gem. § 1618 BGB.",
            "fields": {
                "registry_number": "1847/2020",
                "registry_office": "Standesamt Nürnberg",
                "child_name": "Tim Valentin Becker",
                "effective_date": "2020-09-14",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "Geburtsurkunde": {
        "category": "Urkunden",
        "meta": {
            "title": "Geburtsurkunde — Sindy Hoppe",
            "date": "1990-03-22",
            "document_type": "certificate",
            "tags": ["urkunde", "geburt", "standesamt"],
            "sender": "Standesamt Radebeul",
            "summary": "Geburtsurkunde für Sindy Hoppe, geboren am 22.03.1990 in Radebeul.",
            "fields": {
                "registry_number": "312/1990",
                "registry_office": "Standesamt Radebeul",
                "birth_date": "1990-03-22",
                "birth_place": "Radebeul",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "Scanned_20250119-1838": {
        "category": "Medizin",
        "meta": {
            "title": "Rezept Insulinpumpe Accu-Chek Insight",
            "date": "2025-01-15",
            "document_type": "invoice",
            "tags": ["medizin", "diabetes", "insulinpumpe", "rezept"],
            "sender": "Dr. med. Karin Neumann, Kinder- und Jugendmedizin",
            "summary": "Ärztliche Verordnung einer Accu-Chek Insight Insulinpumpe für Tim Valentin Becker (Diabetes mellitus Typ 1).",
            "fields": {
                "patient": "Tim Valentin Becker",
                "device": "Accu-Chek Insight Insulinpumpe",
                "diagnosis": "Diabetes mellitus Typ 1",
                "amount": 4250.00,
                "currency": "EUR",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "Scanned_20250119-1839": {
        "category": "Medizin",
        "meta": {
            "title": "Rezept Diabetes-Verbrauchsmaterial",
            "date": "2025-01-15",
            "document_type": "invoice",
            "tags": ["medizin", "diabetes", "verbrauchsmaterial"],
            "sender": "Dr. med. Karin Neumann, Kinder- und Jugendmedizin",
            "summary": "Verordnung von Insulin-Katheter-Sets und Reservoiren für die Accu-Chek Insight Pumpe.",
            "fields": {
                "patient": "Tim Valentin Becker",
                "items": "Katheter-Sets, Reservoire",
                "amount": 387.60,
                "currency": "EUR",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "Scanned_20250119-1840": {
        "category": "Medizin",
        "meta": {
            "title": "Debeka Leistungsabrechnung Insulinpumpe",
            "date": "2025-01-18",
            "document_type": "letter",
            "tags": ["medizin", "versicherung", "debeka", "erstattung"],
            "sender": "Debeka Krankenversicherung",
            "summary": "Leistungsabrechnung der Debeka: Erstattung von 3.825,00 EUR für Insulinpumpe und Glukosemesssystem.",
            "fields": {
                "reimbursed_amount": 3825.00,
                "currency": "EUR",
                "policy_number": "DBK-7741928",
                "claim_reference": "LE-2025-00847",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "Scanned_20250119-1840(1)": {
        "category": "Medizin",
        "meta": {
            "title": "BVA Beihilfebescheid Insulinpumpe",
            "date": "2025-01-19",
            "document_type": "letter",
            "tags": ["medizin", "beihilfe", "bva", "insulinpumpe"],
            "sender": "Bundesverwaltungsamt — Beihilfestelle",
            "summary": "Beihilfebescheid: Genehmigung der Beihilfe für Accu-Chek Insight Insulinpumpe gem. § 25 BBhV.",
            "fields": {
                "approved_amount": 2125.00,
                "currency": "EUR",
                "reference": "BVA-BH-2025-4711",
                "regulation": "§ 25 BBhV",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
    "20251016-1123": {
        "category": "Sonstiges",
        "meta": {
            "title": "Bauanleitung Blumentreppe aus Holz",
            "date": "2025-10-16",
            "document_type": "guide",
            "tags": ["diy", "holzbau", "garten", "bauanleitung"],
            "sender": "",
            "summary": "Schritt-für-Schritt-Anleitung zum Bau einer dreistufigen Blumentreppe aus Fichtenholz.",
            "fields": {
                "material_cost": 45.00,
                "currency": "EUR",
                "difficulty": "mittel",
                "time_estimate": "3 Stunden",
            },
            "processing": {
                "ocr_engine": "mistral-ocr-3",
                "classifier": "manual",
                "processed_at": "2025-10-18T12:00:00Z",
                "text_layer_embedded": False,
            },
        },
    },
}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from markdown text."""
    m = FRONTMATTER_RE.match(text)
    return text[m.end() :] if m else text


def main():
    print(f"Source:  md={MD_DIR}  pdf={PDF_DIR}")
    print(f"Target:  {ARCHIVE_DIR}")
    print()

    for name, doc in DOCUMENTS.items():
        category = doc["category"]
        meta = doc["meta"]
        year = str(meta["date"])[:4]

        target_dir = ARCHIVE_DIR / year / category
        target_dir.mkdir(parents=True, exist_ok=True)

        # Copy PDF
        pdf_src = PDF_DIR / f"{name}.pdf"
        pdf_dst = target_dir / f"{name}.pdf"
        if pdf_src.exists():
            shutil.copy2(pdf_src, pdf_dst)
            print(f"  PDF  {pdf_dst.relative_to(DATA_DIR)}")
        else:
            print(f"  WARN  PDF not found: {pdf_src}")

        # Write .md (OCR body without frontmatter)
        md_src = MD_DIR / f"{name}.md"
        md_dst = target_dir / f"{name}.md"
        if md_src.exists():
            body = strip_frontmatter(md_src.read_text(encoding="utf-8"))
            md_dst.write_text(body, encoding="utf-8")
            print(f"  MD   {md_dst.relative_to(DATA_DIR)}")
        else:
            print(f"  WARN  MD not found: {md_src}")

        # Write .meta.yml
        meta_dst = target_dir / f"{name}.meta.yml"
        meta_dst.write_text(
            yaml.dump(meta, default_flow_style=False, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        print(f"  META {meta_dst.relative_to(DATA_DIR)}")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
