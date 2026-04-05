"""Dev server: serves SPA from src/ and data from $SIDECAR_DATA_DIR under one origin."""

import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import unquote

from config import DATA_DIR, get_logger

log = get_logger("server")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(REPO_ROOT, "src")
DATA_ROOT = str(DATA_DIR)
PORT = int(os.environ.get("PORT", "8000"))


class DevHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        path = unquote(path.split("?", 1)[0].split("#", 1)[0])

        # Data routes
        if path.startswith("/archive/") or path.startswith("/pagefind/") or (path.startswith("/manifest-") and path.endswith(".json")):
            resolved = os.path.realpath(os.path.join(DATA_ROOT, path.lstrip("/")))
            if not resolved.startswith(DATA_ROOT):
                return ""  # will 404
            return resolved

        # SPA routes
        rel = path.lstrip("/") or "index.html"
        resolved = os.path.realpath(os.path.join(SRC_DIR, rel))
        if not resolved.startswith(SRC_DIR):
            return ""  # will 404
        return resolved

    def log_message(self, format, *args):
        pass  # suppress per-request logging


def main():
    log.info("SPA:  %s", SRC_DIR)
    log.info("Data: %s", DATA_ROOT)
    log.info("http://localhost:%d", PORT)

    server = HTTPServer(("", PORT), DevHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Stopped.")


if __name__ == "__main__":
    main()
