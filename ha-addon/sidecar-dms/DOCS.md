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

## Intake

Place PDFs into the `intake/` subfolder of the add-on's data directory
(reachable via the Samba or File Editor add-on). New files are picked up
automatically.
</content>
