#!/usr/bin/env python3
"""OCR via OpenRouter file-parser plugin (cloudflare-ai or mistral-ocr engine)."""

import base64
import json
import os
import re
from pathlib import Path

import requests

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OCR_ENGINE = os.environ.get("OCR_ENGINE", "cloudflare-ai")
# Cheap Mistral model — its response is irrelevant, we only want the OCR annotations.
# Using Mistral-hosted model so OCR text stays with the same provider (no third-party training).
MODEL = os.environ.get("OCR_MODEL", "mistralai/mistral-small-3.1-24b-instruct")


def ocr_pdf(pdf_path: Path) -> str:
    """Send PDF to OpenRouter with file-parser plugin, return extracted text."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    b64 = base64.b64encode(pdf_path.read_bytes()).decode()
    data_url = f"data:application/pdf;base64,{b64}"

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Return the document text."},
                    {
                        "type": "file",
                        "file": {
                            "filename": pdf_path.name,
                            "file_data": data_url,
                        },
                    },
                ],
            }
        ],
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
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    # Extract OCR text from annotations
    annotations = (
        data.get("choices", [{}])[0]
        .get("message", {})
        .get("annotations", [])
    )

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

    if text_parts:
        return "\n\n".join(text_parts)

    # Fallback: use the model's response content (some engines inline the text)
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    if content:
        return content

    raise RuntimeError(f"No OCR text in response: {json.dumps(data, indent=2)[:500]}")


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

    text = ocr_pdf(path)
    print(text)
