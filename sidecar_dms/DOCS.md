# Sidecar DMS

Drop PDFs into the intake folder; they get OCR'd, classified, and indexed
for full-text search. UI is served via Ingress.

## Options

| Option              | Description                                        |
| ------------------- | -------------------------------------------------- |
| `openrouter_api_key`| **Required.** OpenRouter API key.                  |
| `openrouter_url`    | Chat completions endpoint.                         |
| `ocr_engine`        | OCR backend identifier.                            |
| `classify_model`    | Classification model.                              |
| `log_level`         | `DEBUG`, `INFO`, `WARNING`, `ERROR`.               |

## Folders

Both folders live under `/share/sidecar-dms/`, reachable via the Samba
share (`\\<ha-host>\share\sidecar-dms\`) or the File Editor add-on:

- `intake/` — drop new PDFs here; they're OCR'd and classified, then moved
  into `archive/`.
- `archive/` — the processed corpus (`<year>/<category>/<name>.pdf` plus
  sidecar `.md` and `.meta.yml`). To import an existing archive, copy it
  here (preserving the directory layout) and restart the add-on; manifests
  and the search index rebuild automatically.
