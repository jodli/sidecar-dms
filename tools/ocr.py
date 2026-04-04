#!/usr/bin/env python3
"""OCR + classification via OpenRouter: mistral-ocr plugin + LLM in one request."""

import base64
import json
import os
import re
from pathlib import Path

import requests

from classify import CLASSIFY_MODEL, SYSTEM_PROMPT, parse_llm_response, validate_metadata, stub_metadata

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OCR_ENGINE = os.environ.get("OCR_ENGINE", "cloudflare-ai")


def ocr_pdf(pdf_path: Path) -> tuple[str, dict]:
    """Send PDF to OpenRouter with mistral-ocr plugin + classification model.

    Returns (ocr_text, metadata_dict).
    OCR text comes from annotations, metadata from the model response.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    b64 = base64.b64encode(pdf_path.read_bytes()).decode()
    data_url = f"data:application/pdf;base64,{b64}"

    payload = {
        "model": CLASSIFY_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Klassifiziere dieses Dokument."},
                    {
                        "type": "file",
                        "file": {
                            "filename": pdf_path.name,
                            "file_data": data_url,
                        },
                    },
                ],
            },
        ],
        "max_tokens": 2048,
        "plugins": [
            {
                "id": "file-parser",
                "pdf": {"engine": OCR_ENGINE},
            }
        ],
    }

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()

    message = data.get("choices", [{}])[0].get("message", {})

    # Extract OCR text from annotations
    ocr_text = _extract_ocr_text(message.get("annotations", []))

    # Extract classification from model response
    model_content = message.get("content", "")
    raw = parse_llm_response(model_content)
    if raw:
        metadata = validate_metadata(raw)
    else:
        print(f"  WARN  Classification failed, using stub. Response: {model_content[:200]}")
        metadata = stub_metadata(pdf_path.stem)

    if not ocr_text:
        # Fallback: use model content as OCR text if no annotations
        if model_content:
            ocr_text = model_content
        else:
            raise RuntimeError(f"No OCR text in response: {json.dumps(data, indent=2)[:500]}")

    return ocr_text, metadata


def _extract_ocr_text(annotations: list) -> str:
    """Extract text from OpenRouter file annotations."""
    text_parts = []
    for ann in annotations:
        if ann.get("type") == "file":
            for part in ann.get("file", {}).get("content", []):
                if part.get("type") == "text":
                    text = part["text"]
                    # Strip <file> wrapper tags that cloudflare-ai adds
                    text = re.sub(r'^<file[^>]*>\s*', '', text)
                    text = re.sub(r'\s*</file>\s*$', '', text)
                    text = text.strip()
                    if text:
                        text_parts.append(text)
    return "\n\n".join(text_parts)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <pdf_path>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    # Load .env from repo root if present
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
        globals()["OPENROUTER_API_KEY"] = os.environ.get("OPENROUTER_API_KEY", "")

    ocr_text, metadata = ocr_pdf(path)
    print("=== OCR TEXT ===")
    print(ocr_text[:500])
    print(f"\n=== METADATA ===")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
