"""crawlcraft.core.scraper — BaseScraper abstract interface & data models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any


class TaskMode(str, Enum):
    """How a task is triggered."""

    ONCE = "once"          # Execute immediately, one-shot
    CRON = "cron"          # Cron expression
    INTERVAL = "interval"  # Fixed interval in seconds


class TaskStatus(str, Enum):
    """Lifecycle states of a task."""

    CREATED = "created"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScraperStatus(str, Enum):
    """Plugin availability status."""

    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


@dataclass
class ScraperMeta:
    """Metadata declared by each scraper plugin."""

    id: str                          # Unique plugin ID, e.g. "weibo-hotsearch"
    name: str                        # Human-readable name
    version: str                     # Semver
    description: str                 # What this scraper does
    author: str | None = None
    topics: list[str] = field(default_factory=list)  # Default output topic(s)


@dataclass
class ScrapeContext:
    """Runtime context passed into each fetch() call."""

    task_id: str
    plugin_id: str
    run_id: str
    config: dict[str, Any]          # Per-task config overrides
    scheduled_at: datetime | None   # When this run was scheduled
    producer: Any = None            # Redpanda producer (injected)


@dataclass
class ScrapeResult:
    """Result returned by a scraper after fetch()."""

    success: bool
    data: list[dict] | None = None
    error: str | None = None
    items_count: int = 0

    def __post_init__(self):
        if self.data is not None:
            self.items_count = len(self.data)


@dataclass
class TaskConfig:
    """Persisted configuration for a scrape task."""

    id: str
    plugin_id: str
    mode: TaskMode
    cron_expr: str | None = None     # For cron/interval mode
    interval_seconds: int | None = None
    config_json: str = "{}"          # Arbitrary JSON config for the plugin
    status: TaskStatus = TaskStatus.CREATED
    created_at: str = ""
    updated_at: str = ""


class BaseScraper(ABC):
    """All scraper plugins must inherit from this class."""

    meta: ScraperMeta
    status: ScraperStatus = ScraperStatus.ACTIVE

    @abstractmethod
    async def fetch(self, ctx: ScrapeContext) -> ScrapeResult:
        """Execute one scrape cycle.

        Args:
            ctx: Runtime context (task_id, config, producer, etc.)

        Returns:
            ScrapeResult with success flag and data or error.
        """
        ...

    def validate_config(self, config: dict) -> bool:
        """Validate per-task configuration.

        Override in subclasses to add custom validation.
        Returns True if config is valid.
        """
        return True

    async def on_install(self) -> None:
        """Called when the plugin is installed. Optional setup hook."""

    async def on_uninstall(self) -> None:
        """Called when the plugin is being removed. Cleanup hook."""
