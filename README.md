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

OCR and classification happen in a single API call via OpenRouter. One API key for everything.

## What's in the box

- **SPA** (`src/`) — Three-panel browser: sidebar tree, PDF viewer (pdf.js), OCR text (marked.js), metadata panel. Pagefind full-text search. No framework, no build step.
- **Pipeline** (`tools/`) — `process_pdf.py` does OCR + classify + archive + rebuild. `watch_intake.py` polls for new PDFs. `build_manifest.py` and `build_search_index.py` regenerate the data layer.
- **Web** — Caddy serves the SPA and archive data. Auto-HTTPS, gzip, SPA-Fallback.

## Setup

```bash
git clone <repo>
cd sidecar-dms
uv venv && uv pip install -r requirements.txt

# API key + config
cp .env.example .env
# Edit .env: set OPENROUTER_API_KEY and SIDECAR_DATA_DIR

# Create data directory
mkdir -p /path/to/sidecar-data/intake
```

Source code lives in the git repo. Data (PDFs, archive, manifests, search index) lives separately — set via `SIDECAR_DATA_DIR`.

## Usage

### Process a single PDF

```bash
SIDECAR_DATA_DIR=/path/to/data uv run python tools/process_pdf.py /path/to/document.pdf
```

### Watch intake folder

```bash
SIDECAR_DATA_DIR=/path/to/data uv run python tools/watch_intake.py
```

Drop PDFs into `$SIDECAR_DATA_DIR/intake/`. They get processed automatically.

### Start the web UI

```bash
# Install Caddy: https://caddyserver.com/docs/install
SIDECAR_DATA_DIR=/path/to/data caddy run --config Caddyfile
```

Open `https://localhost` (or `http://localhost` without domain).

For production with a domain and auto-HTTPS:

```bash
SIDECAR_DOMAIN=dms.example.com \
SIDECAR_DATA_DIR=/srv/sidecar-data \
SIDECAR_SRC_DIR=/opt/sidecar-dms/src \
  caddy run --config Caddyfile
```

### Rebuild manifests and search index

```bash
SIDECAR_DATA_DIR=/path/to/data uv run python tools/build_manifest.py
SIDECAR_DATA_DIR=/path/to/data uv run python tools/build_search_index.py
```

This happens automatically after `process_pdf.py`, but you can run it manually after editing `.meta.yml` files by hand.

### Run tests

```bash
uv pip install -r requirements-dev.txt
uv run pytest tests/ -v
```

## Production deployment

### 1. Install dependencies

```bash
# On the server
git clone <repo> /opt/sidecar-dms
cd /opt/sidecar-dms
uv venv && uv pip install -r requirements.txt

cp .env.example .env
# Edit .env
```

### 2. Caddy (web server)

Install Caddy via package manager or download: https://caddyserver.com/docs/install

Caddy handles HTTPS automatically (Let's Encrypt) when `SIDECAR_DOMAIN` is set to a real domain.

```bash
# Systemd: Caddy usually comes with its own unit.
# Set environment in /etc/caddy/environment or override the unit.
```

### 3. Watch intake (systemd)

```bash
sudo cp deploy/sidecar-watch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sidecar-watch
```

Logs: `journalctl -u sidecar-watch -f`

The service handles SIGTERM gracefully — it finishes the current batch before stopping.

### 4. Health check

```
curl https://dms.example.com/health
# → OK
```

## Environment variables

| Variable | What | Default |
|---|---|---|
| `SIDECAR_DATA_DIR` | Where the archive, manifests, and search index live | `../sidecar-data` |
| `OPENROUTER_API_KEY` | OpenRouter API key (or put it in `.env`) | required |
| `OCR_ENGINE` | LLM for optical character recognition | `mistral-ocr` |
| `CLASSIFY_MODEL` | LLM for classification | `google/gemma-4-31b-it` |
| `OPENROUTER_URL` | API endpoint | `https://openrouter.ai/api/v1/chat/completions` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `SIDECAR_DOMAIN` | Caddy: domain for auto-HTTPS | `localhost` |
| `SIDECAR_SRC_DIR` | Caddy: path to `src/` directory | `./src` |

## Architecture

No database. Three mechanisms:

1. **Manifests** — One `manifest-YYYY.json` per year, rebuilt from `.meta.yml` files. Drives the sidebar tree.
2. **Pagefind** — Static WASM search index, rebuilt from `.md` + `.meta.yml`. Runs client-side.
3. **On-demand fetch** — Click a document, the SPA fetches `.meta.yml` and `.md`/`.pdf` directly.

Everything is a full rebuild. Always consistent, never out of sync. Fast enough at any realistic home archive scale.
