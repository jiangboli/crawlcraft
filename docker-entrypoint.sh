#!/bin/bash
set -euo pipefail

# ─── crawlcraft Docker Entrypoint ─────────────────────────────────
# Seeds the DB with a default HK-IPO task on first run.

DB_PATH="${CRAWL_DATA_DIR:-/data}/crawlcraft.db"

if [ ! -f "$DB_PATH" ]; then
    echo "First start — initializing database and seeding default tasks..."
    
    # Initialize DB by running a quick import (crawlctl imports on first use)
    # Create the default HK-IPO task
    crawlctl task create hk_ipo \
        --cron "0 8 * * *" \
        --config '{"mode": "list"}' \
        --json 2>/dev/null || true

    echo "Default task created: hk_ipo daily at 08:00"
fi

# Dump current task list for the log
echo "Current tasks:"
crawlctl task list --json 2>/dev/null || echo "  (no tasks yet)"

echo "Starting crawlcraft daemon..."
exec "$@"
