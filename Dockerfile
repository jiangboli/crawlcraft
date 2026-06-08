# ── Stage 1: Build ────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies + crawlcraft into a local venv
COPY pyproject.toml .
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --python /opt/venv/bin/python -e .

# ── Stage 2: Runtime ──────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="crawlcraft"
LABEL org.opencontainers.image.description="Lightweight, pluggable scraping engine"
LABEL org.opencontainers.image.source="https://github.com/jiangboli/crawlcraft"

# Runtime deps: kafka-python needs libssl, httpx needs libcurl etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy venv (complete with all deps + crawlcraft installed)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code (used for plugin loading, scrapers, etc.)
COPY src/ /app/src/
COPY pyproject.toml /app/
WORKDIR /app

# Make crawlctl available on PATH via the venv
RUN python3 -m pip install --no-deps --no-build-isolation -e /app 2>/dev/null || true

# Runtime user (non-root)
RUN groupadd -r crawlcraft && useradd -r -g crawlcraft -d /data crawlcraft
RUN mkdir -p /data /plugins && chown -R crawlcraft:crawlcraft /data /plugins

# Volumes
VOLUME ["/data", "/plugins"]

# Entrypoint script (seed tasks on first start)
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8910/health', timeout=3)" || exit 1

USER crawlcraft
ENV CRAWL_DATA_DIR=/data

EXPOSE 8910

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["crawlctl", "daemon", "start"]
