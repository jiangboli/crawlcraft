"""crawlcraft.core.runs — run record management."""

from crawlcraft.store.db import get_db


async def record_run(
    run_id: str,
    task_id: str,
    status: str,
    started_at: str,
    finished_at: str | None = None,
    items_count: int = 0,
    error_message: str | None = None,
):
    """Record a task execution run."""
    db = await get_db()
    await db.execute(
        """INSERT INTO runs (id, task_id, status, started_at, finished_at, items_count, error_message)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (run_id, task_id, status, started_at, finished_at, items_count, error_message),
    )
    await db.commit()


async def list_runs(task_id: str | None = None, limit: int = 20) -> list:
    """List recent runs, optionally filtered by task_id."""
    db = await get_db()
    if task_id:
        rows = await db.execute_fetchall(
            "SELECT * FROM runs WHERE task_id = ? ORDER BY started_at DESC LIMIT ?",
            (task_id, limit),
        )
    else:
        rows = await db.execute_fetchall(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
    return [dict(r) for r in rows]
