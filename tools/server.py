"""Unified ASGI backend: static file serving + intake watcher in one process."""

import asyncio
import contextlib
import os
import re
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from config import DATA_DIR, REPO_ROOT, get_logger
from build_manifest import main as build_manifest_main
from build_search_index import main_async as build_search_index_main_async
from watch_intake import watch_async

log = get_logger("server")

MANIFEST_NAME_RE = re.compile(r"^(?:\d{4}|index)$")


class SpaStaticFiles(StaticFiles):
    """Serve real files when they exist, fall back to index.html otherwise (client-side routing)."""

    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404:
                return FileResponse(Path(self.directory) / "index.html")
            raise


class IngressPathMiddleware:
    """Honor the Home Assistant Ingress X-Ingress-Path header so URL generation
    and StaticFiles serve relative to the ingress prefix instead of /."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            for name, value in scope.get("headers", ()):
                if name == b"x-ingress-path" and value:
                    prefix = value.decode("latin-1").rstrip("/")
                    scope = dict(scope)
                    scope["root_path"] = prefix
                    path = scope.get("path", "")
                    if path.startswith(prefix):
                        scope["path"] = path[len(prefix):] or "/"
                        raw = scope.get("raw_path") or path.encode("latin-1")
                        if raw.startswith(prefix.encode("latin-1")):
                            scope["raw_path"] = raw[len(prefix):] or b"/"
                    break
        await self.app(scope, receive, send)


def create_app(data_dir: Path, src_dir: Path, start_watcher: bool = True) -> Starlette:
    """Build the ASGI app. Pure function — no global state."""

    # Ensure mount directories exist so StaticFiles doesn't crash on fresh installs
    (data_dir / "archive").mkdir(parents=True, exist_ok=True)
    (data_dir / "pagefind").mkdir(parents=True, exist_ok=True)
    (data_dir / "intake").mkdir(parents=True, exist_ok=True)

    async def health(request: Request) -> Response:
        return PlainTextResponse("OK")

    async def manifest(request: Request) -> Response:
        name = request.path_params["name"]
        if not MANIFEST_NAME_RE.match(name):
            return Response(status_code=404)
        path = data_dir / f"manifest-{name}.json"
        if not path.is_file():
            return Response(status_code=404)
        return FileResponse(path, media_type="application/json")

    routes = [
        Route("/health", health),
        Route("/manifest-{name:str}.json", manifest),
    ]

    # Static mounts for data dirs — missing files return 404, no SPA fallback
    routes.append(Mount("/archive", app=StaticFiles(directory=data_dir / "archive")))
    routes.append(Mount("/pagefind", app=StaticFiles(directory=data_dir / "pagefind")))

    # SPA: serve real files from src/, fall back to index.html for client-side routes
    routes.append(Mount("/", app=SpaStaticFiles(directory=src_dir, html=True)))

    middleware = [
        Middleware(IngressPathMiddleware),
        Middleware(GZipMiddleware, minimum_size=1000),
    ]

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        log.info("Rebuilding manifests...")
        build_manifest_main()
        log.info("Rebuilding search index...")
        await build_search_index_main_async()

        stop = asyncio.Event()
        task = None
        if start_watcher:
            task = asyncio.create_task(watch_async(stop))

        try:
            yield
        finally:
            if task:
                stop.set()
                try:
                    await asyncio.wait_for(task, timeout=120)
                except asyncio.TimeoutError:
                    log.warning("Watcher task did not stop within timeout, cancelling")
                    task.cancel()

    return Starlette(routes=routes, middleware=middleware, lifespan=lifespan)


def main():
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "0.0.0.0")
    src_dir = REPO_ROOT / "src"

    app = create_app(data_dir=DATA_DIR, src_dir=src_dir, start_watcher=True)

    log.info("Starting server on %s:%d (data=%s, src=%s)", host, port, DATA_DIR, src_dir)
    uvicorn.run(app, host=host, port=port, log_config=None)


if __name__ == "__main__":
    main()
