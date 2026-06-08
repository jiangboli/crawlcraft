#!/bin/bash
set -euo pipefail

# ─── crawlcraft Docker Helper ──────────────────────────────────────
# Usage: ./docker.sh build | up | down | logs | shell | plugins

CMD=${1:-help}

case "$CMD" in
  build)
    docker compose build crawlcraft
    ;;
  up)
    mkdir -p plugins
    docker compose up -d crawlcraft
    echo "✅ crawlcraft started"
    echo "   Health: http://localhost:8910/health"
    ;;
  down)
    docker compose down
    echo "✅ crawlcraft stopped"
    ;;
  restart)
    docker compose restart crawlcraft
    echo "✅ crawlcraft restarted"
    ;;
  logs)
    docker compose logs -f crawlcraft
    ;;
  shell)
    docker compose exec crawlcraft /bin/bash
    ;;
  plugins)
    echo "Installed plugins in container:"
    docker compose exec crawlcraft crawlctl plugin list
    ;;
  help|*)
    echo "Usage: ./docker.sh <command>"
    echo ""
    echo "Commands:"
    echo "  build      Build the image"
    echo "  up         Start daemon in background"
    echo "  down       Stop daemon"
    echo "  restart    Restart daemon"
    echo "  logs       Tail daemon logs"
    echo "  shell      Open bash inside the container"
    echo "  plugins    List installed scraper plugins"
    echo ""
    echo "Quick start:"
    echo "  cp docker.env.example docker.env   # edit config"
    echo "  ./docker.sh build"
    echo "  ./docker.sh up"
    echo "  ./docker.sh logs"
    ;;
esac
