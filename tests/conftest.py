"""Shared test fixtures for sidecar-dms."""

import sys
from pathlib import Path

import pytest

# Add tools/ to path so tests can import modules directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))


@pytest.fixture
def data_dir(tmp_path):
    """Temporary SIDECAR_DATA_DIR with archive/ and intake/ subdirs."""
    archive = tmp_path / "archive"
    archive.mkdir()
    intake = tmp_path / "intake"
    intake.mkdir()
    return tmp_path


@pytest.fixture
def archive_dir(data_dir):
    """Shortcut to data_dir / archive."""
    return data_dir / "archive"


@pytest.fixture
def intake_dir(data_dir):
    """Shortcut to data_dir / intake."""
    return data_dir / "intake"
