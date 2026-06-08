# crawlcraft

**Lightweight, pluggable scraping engine**

Hot-plug scrapers, cron scheduling, Redpanda output, AI-friendly CLI.

## Quick Start

```bash
# Install
pip install -e .

# Start daemon
crawlctl daemon start

# List available plugins
crawlctl plugin list

# Create a scraping task
crawlctl task create weibo-hotsearch --cron "*/5 * * * *" --start

# Run once
crawlctl task run <task-id>

# AI-friendly output
crawlctl plugin list --json
crawlctl task list --json
```

## Architecture

```
CLI Layer  →  Task Manager  →  Scheduler / Hot-Plug Loader
                                  ↓
                            Scraper Registry
                                  ↓
                            Redpanda Producer
                                  ↓
                            SQLite (state)
```

- **BaseScraper**: Abstract interface for all scrapers
- **Plugin System**: File-system based, hot-reloadable via SIGHUP
- **Scheduler**: APScheduler — cron / interval / once modes
- **Pipeline**: Auto-managed Redpanda topics, one per task
- **CLI**: Click-based, full `--json` support for AI/script consumption

## Project

```text
src/crawlcraft/
├── cli/           # Click CLI commands
├── core/          # Scraper, Task, Scheduler, Plugin Loader
├── pipeline/      # Redpanda producer
└── store/         # SQLite persistence
src/scrapers/      # Built-in scraper plugins
```

## License

MIT
