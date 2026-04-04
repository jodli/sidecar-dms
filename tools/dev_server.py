#!/usr/bin/env python3
"""Dev server: serves SPA from src/ and data from $SIDECAR_DATA_DIR under one origin."""

import os
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
DATA_DIR = Path(os.environ.get("SIDECAR_DATA_DIR", REPO_ROOT.parent.parent / "sidecar-data"))
PORT = int(os.environ.get("PORT", "8000"))


class DevHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        # Strip query string and fragment
        path = path.split("?", 1)[0].split("#", 1)[0]

        # Data routes: archive/, manifest-*.json, pagefind/
        if path.startswith("/archive/") or path.startswith("/pagefind/") or (path.startswith("/manifest-") and path.endswith(".json")):
            return str(DATA_DIR / path.lstrip("/"))

        # SPA routes: everything else served from src/
        rel = path.lstrip("/")
        if not rel or rel == "/":
            rel = "index.html"
        return str(SRC_DIR / rel)


def main():
    print(f"SPA:   {SRC_DIR}")
    print(f"Data:  {DATA_DIR}")
    print(f"http://localhost:{PORT}")
    print()

    handler = partial(DevHandler)
    server = HTTPServer(("", PORT), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
