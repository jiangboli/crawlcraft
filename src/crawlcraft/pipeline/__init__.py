"""crawlcraft.pipeline — data pipeline to Redpanda."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from kafka import KafkaProducer

from crawlcraft.settings import settings

logger = logging.getLogger(__name__)


class RedpandaError(Exception):
    """Raised when Redpanda producer encounters a non-recoverable error."""


@dataclass
class RedpandaConfig:
    """Redpanda connection configuration.

    Defaults are read from environment / .env (via ``crawlcraft.settings``).
    Override any field to customise per-instance.
    """

    bootstrap_servers: str = settings.redpanda_bootstrap_servers
    topic_prefix: str = settings.redpanda_topic_prefix
    batch_size: int = settings.redpanda_batch_size
    linger_ms: int = settings.redpanda_linger_ms
    compression_type: str = settings.redpanda_compression
    acks: str = settings.redpanda_acks
    max_retries: int = settings.redpanda_max_retries


class RedpandaPipeline:
    """Produces scraped data to Redpanda topics.

    One topic per task: ``{prefix}.{plugin_id}.{task_name}``
    """

    def __init__(self, config: RedpandaConfig | None = None):
        self._config = config or RedpandaConfig()
        self._producer: KafkaProducer | None = None

    def connect(self):
        """Initialize the Kafka/Redpanda producer."""
        if self._producer is not None:
            return

        self._producer = KafkaProducer(
            bootstrap_servers=self._config.bootstrap_servers,
            batch_size=self._config.batch_size,
            linger_ms=self._config.linger_ms,
            compression_type=self._config.compression_type,
            acks=self._config.acks,
            max_request_size=10 * 1024 * 1024,  # 10MB
            retries=self._config.max_retries,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        )
        logger.info("Redpanda producer connected to %s", self._config.bootstrap_servers)

    def topic_name(self, plugin_id: str, task_name: str = "default") -> str:
        """Get the topic name for a given plugin + task pair."""
        return f"{self._config.topic_prefix}.{plugin_id}.{task_name}"

    def send(
        self,
        plugin_id: str,
        task_id: str,
        run_id: str,
        data: list[dict],
        task_name: str = "default",
        scheduled_at: str | None = None,
    ) -> int:
        """Send a batch of scraped data to the topic.

        Returns the number of items sent.
        """
        if self._producer is None:
            raise RedpandaError("Producer not connected. Call connect() first.")

        topic = self.topic_name(plugin_id, task_name)

        envelope = {
            "meta": {
                "task_id": task_id,
                "plugin_id": plugin_id,
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "scheduled_at": scheduled_at,
                "count": len(data),
            },
            "data": data,
        }

        future = self._producer.send(topic, value=envelope)
        # Block briefly to catch immediate errors
        future.get(timeout=5)

        logger.info("Sent %d items to topic %s (run=%s)", len(data), topic, run_id)
        return len(data)

    def flush(self):
        """Flush all buffered messages."""
        if self._producer:
            self._producer.flush()

    def close(self):
        """Shut down the producer."""
        if self._producer:
            self._producer.flush()
            self._producer.close(timeout=5)
            self._producer = None
            logger.info("Redpanda producer closed")
