"""crawlcraft.cli.main — click-based CLI entry point."""

from __future__ import annotations

import asyncio
import json
import logging
import sys

import click

from crawlcraft import __version__

logger = logging.getLogger("crawlcraft")


class JsonFormat:
    """Mixin for --json flag support."""

    def __init__(self, json_output: bool):
        self.json_output = json_output

    def emit(self, data):
        if self.json_output:
            click.echo(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            return data


@click.group()
@click.version_option(version=__version__, prog_name="crawlctl")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def cli(ctx, json_output):
    """crawlctl — crawlcraft CLI: scrape task management."""
    ctx.ensure_object(dict)
    ctx.obj["fmt"] = JsonFormat(json_output)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


# ── plugin commands ──────────────────────────────────────────────


@cli.group()
def plugin():
    """Manage scraper plugins."""


@plugin.command("list")
@click.pass_context
def plugin_list(ctx):
    """List all installed scraper plugins."""
    from crawlcraft.core.plugins import load_plugins

    plugins = load_plugins()
    fmt: JsonFormat = ctx.obj["fmt"]

    if fmt.json_output:
        fmt.emit([
            {
                "id": p.meta.id,
                "name": p.meta.name,
                "version": p.meta.version,
                "description": p.meta.description,
                "status": p.status.value,
            }
            for p in plugins.values()
        ])
    else:
        click.echo(f"{'ID':20} {'Name':25} {'Version':10} {'Status':10}")
        click.echo("-" * 70)
        for p in sorted(plugins.values(), key=lambda x: x.meta.id):
            click.echo(f"{p.meta.id:20} {p.meta.name:25} {p.meta.version:10} {p.status.value:10}")


@plugin.command("install")
@click.argument("path_or_url")
def plugin_install(path_or_url):
    """Install a scraper plugin from a local path or remote URL."""
    click.echo(f"Installing plugin from: {path_or_url}")
    click.echo("Feature coming soon.")


@plugin.command("remove")
@click.argument("plugin_id")
def plugin_remove(plugin_id):
    """Remove a scraper plugin."""
    click.echo(f"Removing plugin: {plugin_id}")
    click.echo("Feature coming soon.")


@plugin.command("reload")
def plugin_reload():
    """Hot-reload all scraper plugins from disk."""
    from crawlcraft.core.plugins import reload_plugins, load_plugins

    current = load_plugins()
    updated = reload_plugins(current)
    click.echo(f"Reloaded {len(updated)} plugins (was {len(current)})")


# ── task commands ────────────────────────────────────────────────


@cli.group()
def task():
    """Manage scrape tasks."""


@task.command("create")
@click.argument("plugin_id")
@click.option("--cron", help="Cron expression (e.g. '*/5 * * * *')")
@click.option("--interval", type=int, help="Interval in seconds")
@click.option("--once", "is_once", is_flag=True, help="Run once immediately")
@click.option("--config", help="JSON config string for the plugin")
@click.option("--start", "auto_start", is_flag=True, help="Start immediately after creation")
@click.pass_context
def task_create(ctx, plugin_id, cron, interval, is_once, config, auto_start):
    """Create a new scrape task."""
    from crawlcraft.core import TaskMode
    from crawlcraft.core.task import create_task, update_task_status

    if sum(bool(x) for x in [cron, interval, is_once]) > 1:
        click.echo("Error: Choose only one of --cron, --interval, --once", err=True)
        sys.exit(1)

    if cron:
        mode = TaskMode.CRON
    elif interval:
        mode = TaskMode.INTERVAL
    else:
        mode = TaskMode.ONCE

    cfg = json.loads(config) if config else {}

    # Run in event loop
    async def _create():
        task = await create_task(plugin_id, mode, cron, interval, cfg)
        if auto_start and mode == TaskMode.ONCE:
            from crawlcraft.core.task import get_task
            from crawlcraft.core.scheduler import TaskScheduler

            async def _run(t):
                click.echo(f"  Running task {t.id}...")
                await update_task_status(t.id, TaskMode.ONCE)
                click.echo(f"  Done.")

            sched = TaskScheduler(_run)
            sched.start()
            db_task = await get_task(task.id)
            if db_task:
                sched.add_task(db_task)

        return task

    task_obj = asyncio.run(_create())
    fmt: JsonFormat = ctx.obj["fmt"]

    if fmt.json_output:
        fmt.emit(task_obj.__dict__)
    else:
        click.echo(f"Task created: {task_obj.id}")
        click.echo(f"  Plugin:    {task_obj.plugin_id}")
        click.echo(f"  Mode:      {task_obj.mode.value}")
        click.echo(f"  Cron:      {task_obj.cron_expr or '-'}")
        click.echo(f"  Interval:  {task_obj.interval_seconds or '-'}s")
        click.echo(f"  Status:    {task_obj.status.value}")


@task.command("list")
@click.pass_context
def task_list(ctx):
    """List all tasks."""
    from crawlcraft.core.task import list_tasks

    tasks = asyncio.run(list_tasks())
    fmt: JsonFormat = ctx.obj["fmt"]

    if fmt.json_output:
        fmt.emit([t.__dict__ for t in tasks])
    else:
        click.echo(f"{'ID':10} {'Plugin':20} {'Mode':10} {'Cron/Interval':20} {'Status':12}")
        click.echo("-" * 75)
        for t in tasks:
            schedule = t.cron_expr or f"{t.interval_seconds}s" or "-"
            click.echo(f"{t.id:10} {t.plugin_id:20} {t.mode.value:10} {schedule:20} {t.status.value:12}")


@task.command("start")
@click.argument("task_id")
def task_start(task_id):
    """Start a task immediately (one-shot run)."""
    from crawlcraft.core.task import get_task
    from crawlcraft.core import TaskMode

    task = asyncio.run(get_task(task_id))
    if not task:
        click.echo(f"Task not found: {task_id}", err=True)
        sys.exit(1)

    click.echo(f"Starting task {task_id}...")

    async def _run():
        from crawlcraft.pipeline import RedpandaPipeline
        from crawlcraft.core.plugins import get_plugin

        plugin = get_plugin(task.plugin_id)
        if not plugin:
            click.echo(f"Plugin not found: {task.plugin_id}", err=True)
            return

        pipeline = RedpandaPipeline()
        try:
            pipeline.connect()
            ctx = plugin.ScrapeContext(
                task_id=task.id,
                plugin_id=task.plugin_id,
                run_id=__import__("uuid").uuid4().hex[:12],
                config=json.loads(task.config_json),
                scheduled_at=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
                producer=pipeline,
            )
            result = await plugin.fetch(ctx)
            if result.success and result.data:
                pipeline.send(
                    plugin_id=task.plugin_id,
                    task_id=task.id,
                    run_id=ctx.run_id,
                    data=result.data,
                    scheduled_at=ctx.scheduled_at,
                )
            click.echo(f"  Items: {result.items_count}  Success: {result.success}")
            if result.error:
                click.echo(f"  Error: {result.error}", err=True)
        finally:
            pipeline.close()

    asyncio.run(_run())


@task.command("stop")
@click.argument("task_id")
def task_stop(task_id):
    """Stop/unschedule a task."""
    from crawlcraft.core.task import update_task_status, get_task
    from crawlcraft.core import TaskStatus

    asyncio.run(update_task_status(task_id, TaskStatus.CANCELLED))
    click.echo(f"Task {task_id} stopped.")


@task.command("pause")
@click.argument("task_id")
def task_pause(task_id):
    """Pause a scheduled task."""
    from crawlcraft.core.task import update_task_status
    from crawlcraft.core import TaskStatus

    asyncio.run(update_task_status(task_id, TaskStatus.PAUSED))
    click.echo(f"Task {task_id} paused.")


@task.command("resume")
@click.argument("task_id")
def task_resume(task_id):
    """Resume a paused task."""
    from crawlcraft.core.task import update_task_status
    from crawlcraft.core import TaskStatus

    asyncio.run(update_task_status(task_id, TaskStatus.SCHEDULED))
    click.echo(f"Task {task_id} resumed.")


@task.command("delete")
@click.argument("task_id")
def task_delete(task_id):
    """Delete a task."""
    from crawlcraft.core.task import delete_task

    asyncio.run(delete_task(task_id))
    click.echo(f"Task {task_id} deleted.")


# ── daemon commands ──────────────────────────────────────────────


@cli.group()
def daemon():
    """Manage the crawlcraft background daemon."""


@daemon.command("start")
@click.option("--port", default=8910, help="Health check HTTP port")
def daemon_start(port):
    """Start the background daemon."""
    from crawlcraft.daemon import run_daemon

    click.echo("Starting crawlcraft daemon...")
    asyncio.run(run_daemon(port=port))


@daemon.command("status")
def daemon_status():
    """Check if the daemon is running."""
    import urllib.request
    try:
        resp = urllib.request.urlopen("http://localhost:8910/health", timeout=3)
        data = json.loads(resp.read())
        click.echo("Daemon is running")
        click.echo(f"  Plugins: {data.get('plugins')}")
        click.echo(f"  Tasks:   {data.get('tasks')}")
    except Exception:
        click.echo("Daemon is not running", err=True)
        sys.exit(1)


@daemon.command("stop")
def daemon_stop():
    """Stop the daemon."""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:8910/shutdown", timeout=3)
        click.echo("Daemon shutting down...")
    except Exception:
        click.echo("Daemon not running or already stopped.")


if __name__ == "__main__":
    cli()
