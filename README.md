# Sidecar DMS

Zero-database document archive. PDFs, OCR text, and metadata live as plain files on disk. No app required to understand what's there — `grep` works, `rsync` is the backup strategy.

## How it works

Drop a PDF into the intake folder. The pipeline OCRs it (Mistral OCR), classifies it (Gemma 4 31B), writes sidecar files, and files it into the archive:

```
archive/2024/Rechnungen/
  hornbach-rechnung.pdf          <- original, untouched
  hornbach-rechnung.md           <- OCR text as Markdown
  hornbach-rechnung.meta.yml     <- title, date, type, tags, sender, summary, fields
```

OCR and classification happen in a single API call via OpenRouter. One API key for everything.

## What's in the box

- **SPA** (`src/`) — Three-panel browser: sidebar tree, PDF viewer (pdf.js), OCR text (marked.js), metadata panel. Pagefind full-text search. No framework, no build step.
- **Pipeline** (`tools/`) — `process_pdf.py` does OCR + classify + archive + rebuild. `watch_intake.py` polls for new PDFs. `build_manifest.py` and `build_search_index.py` regenerate the data layer.

## Setup

```bash
# Clone and install
git clone <repo>
cd sidecar-dms
uv venv && uv pip install -r requirements.txt

# API key
echo "OPENROUTER_API_KEY=sk-or-v1-..." > .env

# Create data directory
mkdir -p /path/to/sidecar-data/intake
```

Source code lives in the git repo. Data (PDFs, archive, manifests, search index) lives separately — set via `SIDECAR_DATA_DIR`.

## Usage

### Process a single PDF

```bash
SIDECAR_DATA_DIR=/path/to/sidecar-data uv run python tools/process_pdf.py /path/to/document.pdf
```

### Watch intake folder

```bash
SIDECAR_DATA_DIR=/path/to/sidecar-data uv run python tools/watch_intake.py
```

Drop PDFs into `$SIDECAR_DATA_DIR/intake/`. They get processed automatically.

### Start the web UI

```bash
SIDECAR_DATA_DIR=/path/to/sidecar-data \
  uv run python tools/dev_server.py
```

Open `http://localhost:8000`.

### Rebuild manifests and search index

```bash
SIDECAR_DATA_DIR=/path/to/sidecar-data uv run python tools/build_manifest.py
SIDECAR_DATA_DIR=/path/to/sidecar-data uv run python tools/build_search_index.py
```

This happens automatically after `process_pdf.py`, but you can run it manually after editing `.meta.yml` files by hand.

## Environment variables

| Variable | What | Default |
|---|---|---|
| `SIDECAR_DATA_DIR` | Where the archive, manifests, and search index live | `../sidecar-data` |
| `OPENROUTER_API_KEY` | OpenRouter API key (or put it in `.env`) | required |
| `OCR_ENGINE` | LLM for optical character recognition | `mistral-ocr` |
| `CLASSIFY_MODEL` | LLM for classification | `google/gemma-4-31b-it` |
| `PORT` | Dev server port | `8000` |

## Architecture

No database. Three mechanisms:

1. **Manifests** — One `manifest-YYYY.json` per year, rebuilt from `.meta.yml` files. Drives the sidebar tree.
2. **Pagefind** — Static WASM search index, rebuilt from `.md` + `.meta.yml`. Runs client-side.
3. **On-demand fetch** — Click a document, the SPA fetches `.meta.yml` and `.md`/`.pdf` directly.

Everything is a full rebuild. Always consistent, never out of sync. Fast enough at any realistic home archive scale.
