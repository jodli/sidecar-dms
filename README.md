# Sidecar DMS

Zero-database document archive. PDFs, OCR text, and metadata live as plain files on disk. No app required to understand what's there — `grep` works, `rsync` is the backup strategy.

## How it works

Drop a PDF into the intake folder. The pipeline OCRs it (Mistral OCR), classifies it (Gemma 4 31B), writes sidecar files, and files it into the archive:

```
archive/2024/Rechnungen/
  hornbach-rechnung.pdf          <- original, untouched
  hornbach-rechnung.md           <- OCR text as Markdown
  hornbach-rechnung.meta.yml     <- title, date, kind, category, tags, sender, summary, fields
```

OCR and classification happen in a single API call via OpenRouter.

## Architecture

A single process (`tools/server.py`) runs both:
- **HTTP backend** (Starlette + uvicorn) — serves SPA, archive, pagefind index, manifests
- **Intake watcher** (asyncio task in the same event loop) — polls `$SIDECAR_DATA_DIR/intake/`, OCRs + classifies new PDFs

No database. Data lives on disk:
1. **Manifests** — One `manifest-YYYY.json` per year, rebuilt from `.meta.yml` files. Drives the sidebar tree.
2. **Pagefind** — Static WASM search index, rebuilt from `.md` + `.meta.yml`. Runs client-side.
3. **On-demand fetch** — Click a document, the SPA fetches `.meta.yml` and `.md`/`.pdf` directly.

Everything is a full rebuild. Always consistent, never out of sync.

## Setup

```bash
git clone <repo>
cd sidecar-dms
uv venv && uv pip install -r requirements.txt

cp .env.example .env
# Edit .env: set OPENROUTER_API_KEY and SIDECAR_DATA_DIR

mkdir -p "$SIDECAR_DATA_DIR/intake"
```

## Run

### Server (HTTP + watcher, production)

```bash
SIDECAR_DATA_DIR=/path/to/data uv run python tools/server.py
```

Opens on `http://localhost:8080`. For production, put a reverse proxy (Caddy, Traefik, HA Ingress, Cloudflare Tunnel) in front for TLS.

### Individual pipeline scripts (optional)

```bash
# Process a single PDF manually
uv run python tools/process_pdf.py /path/to/doc.pdf

# Rebuild manifests or search index after hand-editing meta files
uv run python tools/build_manifest.py
uv run python tools/build_search_index.py
```

### Tests

```bash
uv pip install -r requirements-dev.txt
uv run pytest tests/ -v
```

## Deployment (Docker)

```bash
# Set API key
cp .env.example .env && vim .env

# Adjust volume path in docker-compose.yml to point to your data dir
# (must be writable by UID 1000 — the non-root container user)
sudo chown -R 1000:1000 /path/to/sidecar-data

docker compose build
docker compose up -d
docker compose logs -f
```

Container runs as non-root (UID 1000), read-only root filesystem, all capabilities dropped. Mount `/data` volume for persistent storage. For TLS/auth, put a reverse proxy (Caddy, Traefik, HA Ingress, Cloudflare Tunnel) in front.

## Deployment (systemd)

```bash
# On the target host, clone the repo and install deps
git clone <repo> /path/to/sidecar-dms
cd /path/to/sidecar-dms
uv venv && uv pip install -r requirements.txt
cp .env.example .env && vim .env   # set API key + data dir

# Install systemd unit (adjust paths in the file first)
sudo cp deploy/sidecar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sidecar
```

Logs: `journalctl -u sidecar -f`

The service handles SIGTERM gracefully — finishes the current batch before stopping.

## Environment variables

| Variable | What | Default |
|---|---|---|
| `SIDECAR_DATA_DIR` | Where archive, manifests, search index, and intake live | `../sidecar-data` |
| `OPENROUTER_API_KEY` | OpenRouter API key (or put it in `.env`) | required |
| `OCR_ENGINE` | OCR engine | `mistral-ocr` |
| `CLASSIFY_MODEL` | Classification model | `google/gemma-4-31b-it` |
| `OPENROUTER_URL` | API endpoint | `https://openrouter.ai/api/v1/chat/completions` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `HOST` | Server bind address | `0.0.0.0` |
| `PORT` | Server port | `8080` |

## Frontend

Three-panel SPA (`src/`): sidebar tree, PDF viewer (pdf.js), OCR text (marked.js), metadata panel. Pagefind full-text search. No framework, no build step. Vendored libs in `src/vendor/` — no CDN runtime dependencies.
