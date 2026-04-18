#!/bin/sh
set -eu

# When started as root (typical inside Home Assistant add-ons, where the
# Supervisor mounts /data as root:root), make /data writable for the
# unprivileged sidecar user and drop privileges. When started as non-root
# (e.g. docker-compose with `user:` directive), just exec.
if [ "$(id -u)" = "0" ]; then
    chown -R sidecar:sidecar /data
    exec gosu sidecar python tools/server.py
fi
exec python tools/server.py
