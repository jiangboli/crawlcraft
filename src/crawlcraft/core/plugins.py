"""crawlcraft.core.plugins — hot-plug scraper discovery & loader."""

from __future__ import annotations

import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Dict

from crawlcraft.core.scraper import BaseScraper, ScraperMeta, ScraperStatus

logger = logging.getLogger(__name__)

# Plugin search paths (in order)
PLUGIN_PATHS = [
    Path.home() / ".crawlcraft" / "plugins",   # User-installed plugins
    Path(__file__).resolve().parent.parent.parent / "scrapers",  # Built-in scrapers
]

_registry: dict[str, tuple[BaseScraper, str]] = {}  # plugin_id -> (instance, source_path)


def _discover_plugins() -> list[tuple[str, str]]:
    """Scan all plugin paths and return (module_name, path) pairs."""
    found: list[tuple[str, str]] = []
    for base in PLUGIN_PATHS:
        if not base.exists():
            continue
        for entry in sorted(base.iterdir()):
            if not entry.is_dir():
                continue
            # Skip __pycache__ and hidden dirs
            if entry.name.startswith("_") or entry.name.startswith("."):
                continue
            init_file = entry / "__init__.py"
            if init_file.exists():
                found.append((entry.name, str(entry)))
    return found


def load_plugins() -> dict[str, BaseScraper]:
    """Discover, import, and instantiate all scraper plugins.

    Returns a dict of plugin_id -> scraper instance.
    """
    loaded: dict[str, BaseScraper] = {}
    _registry.clear()

    for module_name, path in _discover_plugins():
        parent_dir = str(Path(path).parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        try:
            mod = importlib.import_module(module_name)

            # Find the scraper class (subclass of BaseScraper)
            scraper_cls = None
            for name, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, BaseScraper) and obj is not BaseScraper:
                    scraper_cls = obj
                    break

            if scraper_cls is None:
                logger.warning("No BaseScraper subclass found in plugin %s", module_name)
                continue

            instance: BaseScraper = scraper_cls()
            if not hasattr(instance, "meta") or not isinstance(instance.meta, ScraperMeta):
                logger.warning("Plugin %s missing valid meta attribute", module_name)
                continue

            loaded[instance.meta.id] = instance
            _registry[instance.meta.id] = (instance, path)

        except Exception as exc:
            logger.error("Failed to load plugin %s: %s", module_name, exc)

    return loaded


def reload_plugins(current: dict[str, BaseScraper]) -> dict[str, BaseScraper]:
    """Hot-reload plugins. Re-scans disk and returns an updated registry."""
    # Clear cached modules
    for pid, (_, path) in list(_registry.items()):
        if pid in current:
            mod_name = os.path.basename(path)
            if mod_name in sys.modules:
                del sys.modules[mod_name]

    return load_plugins()


def get_plugin(plugin_id: str) -> BaseScraper | None:
    """Get a loaded plugin by ID."""
    return next(
        (inst for inst, _ in _registry.values() if inst.meta.id == plugin_id),
        None,
    )
