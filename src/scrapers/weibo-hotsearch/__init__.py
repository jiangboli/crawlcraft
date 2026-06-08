"""Scraper plugin: weibo-hotsearch.

Fetches Weibo hot search trends and sends to Redpanda.
"""

from crawlcraft.core.scraper import BaseScraper, ScraperMeta, ScrapeContext, ScrapeResult


class WeiboHotSearchScraper(BaseScraper):
    """Weibo hot search list scraper."""

    meta = ScraperMeta(
        id="weibo-hotsearch",
        name="微博热搜",
        version="0.1.0",
        description="抓取微博热搜榜，定时输出到 Redpanda",
        author="crawlcraft",
        topics=["weibo-hotsearch"],
    )

    async def fetch(self, ctx: ScrapeContext) -> ScrapeResult:
        """Fetch Weibo hot search list."""
        import httpx

        try:
            # Weibo hot search API (public endpoint, no auth)
            url = "https://weibo.com/ajax/side/hotSearch"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            realtime = data.get("data", {}).get("realtime", [])
            items = []
            for entry in realtime:
                items.append({
                    "rank": entry.get("rank"),
                    "keyword": entry.get("word"),
                    "heat": entry.get("raw_hot", 0),
                    "category": entry.get("category"),
                    "icon_desc": entry.get("icon_desc"),
                })

            return ScrapeResult(success=True, data=items)

        except Exception as exc:
            return ScrapeResult(success=False, error=str(exc))

    def validate_config(self, config: dict) -> bool:
        """Basic config validation."""
        return True
