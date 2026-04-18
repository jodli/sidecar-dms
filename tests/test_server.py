"""Tests for server.py: manifest routing, SPA fallback, watcher lifecycle."""

import asyncio
import json
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from server import create_app


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"


@pytest.fixture(autouse=True)
def _stub_rebuilds(monkeypatch):
    """Prevent startup rebuilds from touching global config-driven paths."""
    async def _noop_async():
        return 0

    monkeypatch.setattr("server.build_manifest_main", lambda: 0)
    monkeypatch.setattr("server.build_search_index_main_async", _noop_async)


@pytest.fixture
def app_client(data_dir):
    """TestClient without watcher, using a tmp data dir + real src/."""
    app = create_app(data_dir=data_dir, src_dir=SRC_DIR, start_watcher=False)
    with TestClient(app) as client:
        yield client


class TestManifestRouting:
    def test_existing_manifest_returns_content(self, app_client, data_dir):
        (data_dir / "manifest-2024.json").write_text('[{"path":"foo"}]')

        resp = app_client.get("/manifest-2024.json")

        assert resp.status_code == 200
        assert resp.json() == [{"path": "foo"}]

    def test_manifest_index_returns_content(self, app_client, data_dir):
        (data_dir / "manifest-index.json").write_text('["2024","2023"]')

        resp = app_client.get("/manifest-index.json")

        assert resp.status_code == 200
        assert resp.json() == ["2024", "2023"]

    def test_missing_manifest_404(self, app_client):
        assert app_client.get("/manifest-9999.json").status_code == 404
        assert app_client.get("/manifest-index.json").status_code == 404


class TestSpaFallback:
    def test_root_returns_index_html(self, app_client):
        resp = app_client.get("/")
        assert resp.status_code == 200
        assert b"<title>Sidecar DMS</title>" in resp.content

    def test_unknown_path_returns_index_html(self, app_client):
        """SPA routing: unknown paths fall back to index.html for client-side routing."""
        resp = app_client.get("/documents/some-id")
        assert resp.status_code == 200
        assert b"<title>Sidecar DMS</title>" in resp.content

    def test_missing_archive_file_404_no_fallback(self, app_client):
        """Missing archive files must 404, NOT fall back to index.html."""
        resp = app_client.get("/archive/does/not/exist.pdf")
        assert resp.status_code == 404

    def test_missing_pagefind_file_404_no_fallback(self, app_client):
        resp = app_client.get("/pagefind/missing.js")
        assert resp.status_code == 404

    def test_existing_static_file_served(self, app_client):
        """Real src/ files are served directly, not via fallback."""
        resp = app_client.get("/app.js")
        assert resp.status_code == 200
        assert b"DOMContentLoaded" in resp.content


class TestWatcherLifecycle:
    def test_watcher_starts_and_stops_cleanly(self, data_dir, monkeypatch):
        """Lifespan: start_watcher=True spawns watch_async, shutdown stops it."""
        started = asyncio.Event()
        stopped = False

        async def fake_watch(stop):
            started.set()
            await stop.wait()
            nonlocal stopped
            stopped = True

        monkeypatch.setattr("server.watch_async", fake_watch)

        app = create_app(data_dir=data_dir, src_dir=SRC_DIR, start_watcher=True)
        with TestClient(app) as client:
            # Inside the context: lifespan startup ran, watcher task is active
            assert client.get("/manifest-index.json").status_code in (200, 404)

        # After context exit: lifespan shutdown ran
        assert stopped, "watch_async did not exit after stop event"

    def test_startup_runs_rebuilds(self, data_dir, monkeypatch):
        """Startup calls build_manifest.main() and build_search_index.main_async()."""
        manifest_called = False
        search_called = False

        def fake_manifest():
            nonlocal manifest_called
            manifest_called = True
            return 0

        async def fake_search():
            nonlocal search_called
            search_called = True
            return 0

        async def fake_watch(stop):
            await stop.wait()

        monkeypatch.setattr("server.build_manifest_main", fake_manifest)
        monkeypatch.setattr("server.build_search_index_main_async", fake_search)
        monkeypatch.setattr("server.watch_async", fake_watch)

        app = create_app(data_dir=data_dir, src_dir=SRC_DIR, start_watcher=True)
        with TestClient(app):
            pass

        assert manifest_called
        assert search_called
