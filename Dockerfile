# ── Stage 1: Build ────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster pip
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (layer caching)
COPY pyproject.toml .
RUN uv pip install --system -e . && \
    uv pip install --system gunicorn  # not used yet, but for future

# ── Stage 2: Runtime ──────────────────────────────────────────────
FROM python:3.12-slim

LABEL org.opencontainers.image.title="crawlcraft"
LABEL org.opencontainers.image.description="Lightweight, pluggable scraping engine"
LABEL org.opencontainers.image.source="https://github.com/jiangboli/crawlcraft"

# Runtime deps: kafka-python needs libssl, httpx needs libcurl etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ /app/src/
COPY pyproject.toml /app/
WORKDIR /app

# Make crawlctl available
RUN pip install -e /app --no-deps --no-build-isolation 2>/dev/null || true

# Runtime user (non-root)
RUN groupadd -r crawlcraft && useradd -r -g crawlcraft -d /data crawlcraft
RUN mkdir -p /data /plugins && chown -R crawlcraft:crawlcraft /data /plugins

# Volumes
VOLUME ["/data", "/plugins"]

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8910/health', timeout=3)" || exit 1

USER crawlcraft
ENV CRAWL_DATA_DIR=/data

EXPOSE 8910

ENTRYPOINT ["crawlctl"]
CMD ["daemon", "start"]
