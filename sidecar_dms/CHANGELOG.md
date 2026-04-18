# Changelog

## 0.1.3

- Also expose `archive/` at `/share/sidecar-dms/archive` so an existing
  archive corpus can be imported by copying it there. Manifests and the
  pagefind index are rebuilt automatically on next start.

## 0.1.2

- Expose intake folder at `/share/sidecar-dms/intake` (visible via Samba /
  File Editor). Existing intake files in `/data` are migrated automatically.

## 0.1.1

- Fix `/data` permission denied: entrypoint chowns the volume and drops to
  the unprivileged user via gosu when started as root (HA case).

## 0.1.0

- Initial Home Assistant add-on packaging.
