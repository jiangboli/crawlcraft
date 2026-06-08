"""crawlcraft.core.scheduler — task scheduler backed by APScheduler."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from crawlcraft.core import TaskConfig, TaskMode, TaskStatus
from crawlcraft.core.task import update_task_status

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Manages scheduled execution of scrape tasks.

    Wraps APScheduler's AsyncIOScheduler with crawlcraft-specific lifecycle.
    """

    def __init__(self, run_fn: Callable):
        self._scheduler = AsyncIOScheduler()
        self._run_fn = run_fn  # async callable(task_config) -> None
        self._job_map: dict[str, str] = {}  # task_id -> apscheduler job_id

    def start(self):
        self._scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self, wait: bool = True):
        self._scheduler.shutdown(wait=wait)
        logger.info("Scheduler shut down")

    def add_task(self, task: TaskConfig) -> bool:
        """Schedule a task according to its mode. Returns True on success."""
        if task.status == TaskStatus.PAUSED:
            return False

        async def wrapper():
            await self._run_fn(task)

        task_id = task.id
        job_id = None

        try:
            if task.mode == TaskMode.CRON and task.cron_expr:
                trigger = CronTrigger.from_crontab(task.cron_expr)
                job_id = self._scheduler.add_job(wrapper, trigger, id=task_id).id

            elif task.mode == TaskMode.INTERVAL and task.interval_seconds:
                trigger = IntervalTrigger(seconds=task.interval_seconds)
                job_id = self._scheduler.add_job(wrapper, trigger, id=task_id).id

            elif task.mode == TaskMode.ONCE:
                job_id = self._scheduler.add_job(wrapper, id=task_id).id

            self._job_map[task_id] = job_id
            return True

        except Exception as exc:
            logger.error("Failed to schedule task %s: %s", task_id, exc)
            return False

    def remove_task(self, task_id: str) -> bool:
        """Unschedule a task."""
        job_id = self._job_map.pop(task_id, None)
        if job_id and self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            return True
        return False

    def pause_task(self, task_id: str) -> bool:
        """Pause a scheduled task."""
        job_id = self._job_map.get(task_id)
        if job_id:
            self._scheduler.pause_job(job_id)
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        job_id = self._job_map.get(task_id)
        if job_id:
            self._scheduler.resume_job(job_id)
            return True
        return False

    def get_jobs(self) -> list[dict]:
        """Return list of scheduled jobs for inspection."""
        return [
            {"id": j.id, "next_run_time": str(j.next_run_time) if j.next_run_time else None}
            for j in self._scheduler.get_jobs()
        ]
