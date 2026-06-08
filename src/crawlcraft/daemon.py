"""crawlcraft.daemon — background daemon process."""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from functools import partial

from crawlcraft.core.plugins import load_plugins
from crawlcraft.core.task import list_tasks
from crawlcraft.pipeline import RedpandaPipeline
from crawlcraft.settings import settings

logger = logging.getLogger(__name__)


async def run_daemon(port: int | None = None):
    """Main daemon entry point.

    Starts:
    1. Plugin loader (discover & cache all plugins)
    2. Scheduler (load tasks from DB, schedule them)
    3. HTTP health check server
    4. Signal handlers for graceful shutdown & hot-reload
    """

    if port is None:
        port = settings.daemon_port

    # Load plugins
    logger.info("Loading plugins...")
    plugins = load_plugins()
    logger.info("Loaded %d plugins", len(plugins))

    # Load tasks from DB
    tasks = await list_tasks()
    logger.info("Loaded %d tasks from DB", len(tasks))

    # Initialise pipeline (but don't connect yet — lazily connect on first use)
    pipeline = RedpandaPipeline()

    # Set up scheduler
    from crawlcraft.core.scheduler import TaskScheduler

    async def run_task(task_config):
        """Callback invoked by the scheduler for each task tick."""
        plugin = plugins.get(task_config.plugin_id)
        if not plugin:
            logger.error("Plugin %s not found for task %s", task_config.plugin_id, task_config.id)
            return

        from crawlcraft.core import ScrapeContext
        from datetime import datetime, timezone
        import uuid

        try:
            pipeline.connect()

            ctx = ScrapeContext(
                task_id=task_config.id,
                plugin_id=task_config.plugin_id,
                run_id=uuid.uuid4().hex[:12],
                config=json.loads(task_config.config_json),
                scheduled_at=datetime.now(timezone.utc).isoformat(),
                producer=pipeline,
            )
            result = await plugin.fetch(ctx)
            if result.success and result.data:
                pipeline.send(
                    plugin_id=task_config.plugin_id,
                    task_id=task_config.id,
                    run_id=ctx.run_id,
                    data=result.data,
                    scheduled_at=ctx.scheduled_at,
                )
            logger.info(
                "Task %s completed: %d items, success=%s",
                task_config.id, result.items_count, result.success,
            )
        except Exception as exc:
            logger.error("Task %s failed: %s", task_config.id, exc)

    scheduler = TaskScheduler(run_task)
    scheduler.start()

    # Schedule persisted tasks
    for task in tasks:
        scheduler.add_task(task)

    # Simple HTTP health check
    server = await _start_health_server(port, plugins, scheduler)

    logger.info("Daemon started on port %d", port)
    logger.info("  Plugins: %d  Tasks: %d", len(plugins), len(tasks))

    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    stop_event = asyncio.Event()

    def _shutdown():
        logger.info("Shutting down...")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            # Windows or non-main-loop workaround
            pass

    await stop_event.wait()

    # Graceful shutdown
    scheduler.shutdown(wait=True)
    pipeline.close()
    server.close()
    logger.info("Daemon stopped.")


async def _start_health_server(port, plugins, scheduler):
    """Minimal async HTTP server for health checks."""

    async def handle_request(reader, writer):
        """Async health check handler."""
        # Read and discard the request
        await reader.read(1024)
        data = json.dumps({
            "status": "ok",
            "plugins": len(plugins),
            "tasks": len(scheduler.get_jobs()),
        })
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(data)}\r\n"
            "\r\n"
            f"{data}"
        )
        writer.write(response.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(
        handle_request,
        host=settings.daemon_host,
        port=port,
    )
    return server
