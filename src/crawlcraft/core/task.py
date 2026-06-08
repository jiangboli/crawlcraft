"""crawlcraft.core.task — task model and state management."""

from __future__ import annotations

from crawlcraft.core import TaskConfig, TaskStatus, TaskMode
from crawlcraft.store.db import get_db


async def create_task(
    plugin_id: str,
    mode: TaskMode,
    cron_expr: str | None = None,
    interval_seconds: int | None = None,
    config: dict | None = None,
) -> TaskConfig:
    """Create a new scrape task."""
    import uuid
    from datetime import datetime, timezone

    task = TaskConfig(
        id=str(uuid.uuid4())[:8],
        plugin_id=plugin_id,
        mode=mode,
        cron_expr=cron_expr,
        interval_seconds=interval_seconds,
        config_json=__import__("json").dumps(config or {}),
        status=TaskStatus.CREATED,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )

    db = await get_db()
    await db.execute(
        """INSERT INTO tasks (id, plugin_id, mode, cron_expr, interval_seconds, config_json, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (task.id, task.plugin_id, task.mode.value, task.cron_expr,
         task.interval_seconds, task.config_json, task.status.value,
         task.created_at, task.updated_at),
    )
    await db.commit()
    return task


async def list_tasks() -> list[TaskConfig]:
    """List all tasks."""
    db = await get_db()
    rows = await db.execute_fetchall("SELECT * FROM tasks ORDER BY created_at DESC")
    return [_row_to_task(r) for r in rows]


async def get_task(task_id: str) -> TaskConfig | None:
    """Get a single task by ID."""
    db = await get_db()
    rows = await db.execute_fetchall("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return _row_to_task(rows[0]) if rows else None


async def update_task_status(task_id: str, status: TaskStatus) -> None:
    """Update task status."""
    from datetime import datetime, timezone
    db = await get_db()
    await db.execute(
        "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
        (status.value, datetime.now(timezone.utc).isoformat(), task_id),
    )
    await db.commit()


async def delete_task(task_id: str) -> None:
    """Delete a task."""
    db = await get_db()
    await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    await db.commit()


def _row_to_task(row) -> TaskConfig:
    return TaskConfig(
        id=row[0],
        plugin_id=row[1],
        mode=TaskMode(row[2]),
        cron_expr=row[3],
        interval_seconds=row[4],
        config_json=row[5],
        status=TaskStatus(row[6]),
        created_at=row[7],
        updated_at=row[8],
    )
