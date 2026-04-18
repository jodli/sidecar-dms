#!/bin/sh
set -eu

SHARE_DIR=/share/sidecar-dms
SHARE_INTAKE=$SHARE_DIR/intake
DATA_INTAKE=/data/intake

# In the HA add-on context /share is mounted (via `map: share:rw`). Expose
# intake/ there so users can drop PDFs via Samba / File Editor instead of
# poking around in the add-on's private /data. /data/intake becomes a
# symlink into /share. archive/ stays in /data (persistent, not user-managed).
if [ "$(id -u)" = "0" ] && [ -d /share ]; then
    mkdir -p "$SHARE_INTAKE"
    chown sidecar:sidecar "$SHARE_DIR" "$SHARE_INTAKE"

    if [ ! -L "$DATA_INTAKE" ]; then
        if [ -d "$DATA_INTAKE" ]; then
            # Migrate any pre-existing intake files into /share.
            mv "$DATA_INTAKE"/* "$SHARE_INTAKE"/ 2>/dev/null || true
            rmdir "$DATA_INTAKE" 2>/dev/null || rm -rf "$DATA_INTAKE"
        fi
        ln -s "$SHARE_INTAKE" "$DATA_INTAKE"
    fi
fi

# When started as root (typical inside Home Assistant add-ons, where the
# Supervisor mounts /data as root:root), make /data writable for the
# unprivileged sidecar user and drop privileges. When started as non-root
# (e.g. docker-compose with `user:` directive), just exec.
if [ "$(id -u)" = "0" ]; then
    chown -R sidecar:sidecar /data
    exec gosu sidecar python tools/server.py
fi
exec python tools/server.py
