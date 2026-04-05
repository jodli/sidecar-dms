"""OCR + classification via OpenRouter: mistral-ocr plugin + LLM in one request."""

import base64
import json
import re
import time
from pathlib import Path

import requests

from config import OPENROUTER_API_KEY, OPENROUTER_URL, OCR_ENGINE, CLASSIFY_MODEL, get_logger
from classify import SYSTEM_PROMPT, ClassificationError, parse_llm_response, validate_metadata

log = get_logger("ocr")

MAX_RETRIES = 2
RETRY_BACKOFF = 2  # seconds, doubled each retry
TRANSIENT_CODES = {429, 500, 502, 503, 504}


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

    data = _request_with_retry(payload)
    message = data.get("choices", [{}])[0].get("message", {})

    # Extract OCR text from annotations
    ocr_text = _extract_ocr_text(message.get("annotations", []))
    if not ocr_text:
        raise RuntimeError("Kein OCR-Text in API-Antwort (Annotations leer)")

    # Extract classification from model response
    model_content = message.get("content", "")
    raw = parse_llm_response(model_content)
    if not raw:
        raise ClassificationError(
            f"Klassifikation fehlgeschlagen — kein JSON in Antwort: {model_content[:200]}"
        )
    metadata = validate_metadata(raw)

    return ocr_text, metadata


def _request_with_retry(payload: dict) -> dict:
    """POST to OpenRouter with retry on transient failures."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=180)

            if resp.status_code in TRANSIENT_CODES and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * (2 ** attempt)
                log.warning("HTTP %d, retrying in %ds...", resp.status_code, wait)
                time.sleep(wait)
                continue

            resp.raise_for_status()

            try:
                return resp.json()
            except (json.JSONDecodeError, ValueError) as e:
                raise RuntimeError(f"Invalid JSON response: {resp.text[:200]}") from e

        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * (2 ** attempt)
                log.warning("Network error: %s. Retrying in %ds...", e, wait)
                time.sleep(wait)
                continue
            raise RuntimeError(f"API unreachable after {MAX_RETRIES + 1} attempts") from e

    raise last_error or RuntimeError("Request failed")


def _extract_ocr_text(annotations: list) -> str:
    """Extract text from OpenRouter file annotations."""
    text_parts = []
    for ann in annotations:
        if ann.get("type") == "file":
            for part in ann.get("file", {}).get("content", []):
                if part.get("type") == "text":
                    text = part["text"]
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
    ocr_text, metadata = ocr_pdf(path)
    print("=== OCR TEXT ===")
    print(ocr_text[:500])
    print(f"\n=== METADATA ===")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
