#!/bin/sh
set -e

# Run database migrations once before launching multi-worker server
if [ "$RUN_MIGRATIONS" != "false" ]; then
    echo "Running database schema migrations..."
    python -m alembic upgrade head
fi

exec "$@"
