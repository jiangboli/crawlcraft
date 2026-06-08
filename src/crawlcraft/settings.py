"""crawlcraft.settings — central configuration via pydantic-settings.

Reads from environment variables or .env file, with sensible defaults.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application-wide configuration.

    Loads from environment variables or .env file.
    Prefix all env vars with ``CRAWL_``.
    """

    model_config = SettingsConfigDict(
        env_prefix="CRAWL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Redpanda ──────────────────────────────────────────────────
    redpanda_bootstrap_servers: str = Field(
        default="172.16.10.3:9092",
        description="Redpanda/Kafka bootstrap server address",
    )
    redpanda_topic_prefix: str = Field(
        default="crawl",
        description="Prefix for all auto-created topics",
    )
    redpanda_batch_size: int = Field(default=16384, ge=1)
    redpanda_linger_ms: int = Field(default=1000, ge=0)
    redpanda_compression: str = Field(default="lz4")
    redpanda_acks: str = Field(default="1")
    redpanda_max_retries: int = Field(default=3, ge=0)

    # ── Daemon ────────────────────────────────────────────────────
    daemon_port: int = Field(default=8910, description="Health check HTTP port")
    daemon_host: str = Field(default="127.0.0.1")

    # ── Data ──────────────────────────────────────────────────────
    data_dir: str = Field(default="~/.crawlcraft", description="Data directory for DB & logs")


# Global singleton
settings = Settings()
