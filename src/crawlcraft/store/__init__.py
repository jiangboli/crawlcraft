"""crawlcraft.store.db — SQLite persistence layer."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from crawlcraft.settings import settings

import aiosqlite

logger = logging.getLogger(__name__)

DATA_DIR = Path(os.path.expanduser(settings.data_dir))
DB_PATH = DATA_DIR / "crawlcraft.db"

_conn: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Get or create the shared async SQLite connection."""
    global _conn
    if _conn is not None:
        return _conn

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    _conn = await aiosqlite.connect(str(DB_PATH))
    _conn.row_factory = aiosqlite.Row
    await _init_schema(_conn)
    return _conn


async def close_db():
    """Close the database connection."""
    global _conn
    if _conn:
        await _conn.close()
        _conn = None


async def _init_schema(db: aiosqlite.Connection):
    """Create tables if they don't exist."""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS plugins (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            version     TEXT,
            path        TEXT,
            enabled     INTEGER DEFAULT 1,
            installed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id              TEXT PRIMARY KEY,
            plugin_id       TEXT NOT NULL,
            mode            TEXT NOT NULL,
            cron_expr       TEXT,
            interval_seconds INTEGER,
            config_json     TEXT DEFAULT '{}',
            status          TEXT DEFAULT 'created',
            created_at      TEXT,
            updated_at      TEXT
        );

        CREATE TABLE IF NOT EXISTS runs (
            id          TEXT PRIMARY KEY,
            task_id     TEXT NOT NULL,
            status      TEXT,
            started_at  TEXT,
            finished_at TEXT,
            items_count INTEGER DEFAULT 0,
            error_message TEXT
        );
    """)
    await db.commit()
