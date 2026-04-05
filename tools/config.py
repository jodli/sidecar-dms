"""Shared configuration: paths, env loading, logging setup."""

import logging
import os
from pathlib import Path

# Repo and data paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("SIDECAR_DATA_DIR", REPO_ROOT.parent / "sidecar-data"))
ARCHIVE_DIR = DATA_DIR / "archive"
INTAKE_DIR = DATA_DIR / "intake"

# Load .env from repo root (once, at import time)
_env_file = REPO_ROOT / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# API config
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OCR_ENGINE = os.environ.get("OCR_ENGINE", "cloudflare-ai")
CLASSIFY_MODEL = os.environ.get("CLASSIFY_MODEL", "google/gemma-4-31b-it")


def get_logger(name: str) -> logging.Logger:
    """Return a logger with timestamp + level format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(name)s: %(message)s", datefmt="%H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
