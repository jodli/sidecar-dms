"""Tests for config.py: dotenv loading, path defaults, logging setup."""

import logging
import os
from unittest.mock import patch

from config import load_dotenv, get_logger


class TestLoadDotenv:
    def test_parses_key_value(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\n")
        assert load_dotenv(env_file) == {"FOO": "bar"}

    def test_ignores_comments(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\nFOO=bar\n")
        assert load_dotenv(env_file) == {"FOO": "bar"}

    def test_handles_equals_in_value(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value=with=equals\n")
        assert load_dotenv(env_file) == {"KEY": "value=with=equals"}

    def test_strips_whitespace(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("  FOO  =  bar  \n")
        assert load_dotenv(env_file) == {"FOO": "bar"}

    def test_skips_empty_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("\n\nFOO=bar\n\n")
        assert load_dotenv(env_file) == {"FOO": "bar"}

    def test_missing_file_returns_empty(self, tmp_path):
        assert load_dotenv(tmp_path / "nonexistent") == {}


class TestGetLogger:
    def test_returns_named_logger(self):
        log = get_logger("test-module")
        assert log.name == "test-module"
        assert isinstance(log, logging.Logger)

    def test_log_level_from_env(self):
        with patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}):
            log = get_logger("test-debug-level")
            assert log.level == logging.DEBUG

    def test_default_log_level_info(self):
        with patch.dict(os.environ, {"LOG_LEVEL": ""}, clear=False):
            log = get_logger("test-default-level")
            assert log.level == logging.INFO
