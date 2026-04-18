"""Shared configuration: paths, env loading, logging setup."""

import json
import logging
import os
from pathlib import Path

# Repo and data paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("SIDECAR_DATA_DIR", REPO_ROOT.parent / "sidecar-data"))
ARCHIVE_DIR = DATA_DIR / "archive"
INTAKE_DIR = DATA_DIR / "intake"

# Home Assistant Supervisor writes user options here. Snake_case keys are
# mapped to UPPER_CASE environment variables, matching our env-driven config.
HA_OPTIONS_PATH = Path("/data/options.json")


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


def load_ha_options(path: Path) -> dict[str, str]:
    """Read Home Assistant addon options. Returns empty dict if file missing."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return {k.upper(): str(v) for k, v in data.items() if v is not None and v != ""}


# Source priority (first wins via setdefault):
# 1. Process environment (e.g. docker-compose, shell)
# 2. HA Supervisor options (/data/options.json) — only present in addon context
# 3. .env at repo root (dev fallback)
for _k, _v in load_ha_options(HA_OPTIONS_PATH).items():
    os.environ.setdefault(_k, _v)
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
