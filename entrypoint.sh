#!/bin/sh
# Fix ownership of the data directory at container startup.
#
# Why this exists: the Dockerfile runs the app as a non-root user for
# security, but bind-mounted host directories (e.g. ./vol1/.../data:/app/data)
# are owned by whoever created them on the host — usually root via the
# Docker daemon. The image's own chown only applies to the in-image
# directory, not to whatever gets mounted on top. So at runtime we
# re-chown the mountpoint to the app user, gracefully no-op'ing if it
# isn't writable (e.g. read-only volume).
set -e

DATA_DIR="$(dirname "$SCOREBOARD_DB")"
if [ -d "$DATA_DIR" ]; then
    chown -R app:app "$DATA_DIR" 2>/dev/null || true
fi

# exec the CMD (uvicorn) as PID 1 so it receives signals properly.
exec "$@"
