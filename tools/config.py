"""Shared configuration: paths, env loading, logging setup."""

import logging
import os
from pathlib import Path

# Repo and data paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("SIDECAR_DATA_DIR", REPO_ROOT.parent / "sidecar-data"))
ARCHIVE_DIR = DATA_DIR / "archive"
INTAKE_DIR = DATA_DIR / "intake"


def load_dotenv(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict. Returns empty dict if file missing."""
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[k.strip()] = v.strip()
    return result


# Load .env from repo root (once, at import time)
for _k, _v in load_dotenv(REPO_ROOT / ".env").items():
    os.environ.setdefault(_k, _v)

# API config
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = os.environ.get("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
OCR_ENGINE = os.environ.get("OCR_ENGINE", "mistral-ocr")
CLASSIFY_MODEL = os.environ.get("CLASSIFY_MODEL", "google/gemma-4-31b-it")


def get_logger(name: str) -> logging.Logger:
    """Return a logger with timestamp + level format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(name)s: %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(handler)
        level = os.environ.get("LOG_LEVEL", "").upper()
        logger.setLevel(getattr(logging, level, logging.INFO))
    return logger
