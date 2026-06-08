"""crawlcraft.store.db — re-export for backwards compat."""

from crawlcraft.store import get_db, close_db, DB_PATH

__all__ = ["get_db", "close_db", "DB_PATH"]
