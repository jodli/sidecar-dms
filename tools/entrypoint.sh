#!/bin/sh
set -eu

SHARE_DIR=/share/sidecar-dms

# In the HA add-on context /share is mounted (via `map: share:rw`). Expose
# the user-managed folders there (intake for new PDFs, archive for the
# processed corpus) so they're reachable via Samba / File Editor instead
# of being trapped in the add-on's private /data. Generated artifacts
# (pagefind index, manifests) stay in /data.
link_to_share() {
    src=$1
    dst=$2
    mkdir -p "$dst"
    chown sidecar:sidecar "$dst"
    [ -L "$src" ] && return 0
    if [ -d "$src" ]; then
        # Migrate any pre-existing contents (incl. dotfiles, subdirs) into
        # /share, then drop the dir so we can replace it with a symlink.
        find "$src" -mindepth 1 -maxdepth 1 -exec mv -t "$dst/" {} + 2>/dev/null || true
        rmdir "$src" 2>/dev/null || rm -rf "$src"
    fi
    ln -s "$dst" "$src"
}

if [ "$(id -u)" = "0" ] && [ -d /share ]; then
    mkdir -p "$SHARE_DIR"
    chown sidecar:sidecar "$SHARE_DIR"

    link_to_share /data/intake "$SHARE_DIR/intake"
    link_to_share /data/archive "$SHARE_DIR/archive"
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
