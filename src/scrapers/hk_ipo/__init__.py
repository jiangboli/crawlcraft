"""Scraper plugin: hk-ipo.

Fetches Hong Kong IPO data from jinwucj.com (金吾财经).
Supports: new subscriptions, pending listings, recent listings,
filed IPOs, detailed offering info, margin data, placement results.
"""

from crawlcraft.core.scraper import BaseScraper, ScraperMeta, ScrapeContext, ScrapeResult

ENDPOINTS = {
    "latest_subscriptions": {
        "url": "https://ipo.jinwucj.com/api/makeNew/makeNewList",
        "label": "最新认购",
    },
    "pending_listings": {
        "url": "https://ipo.jinwucj.com/api/makeNew/getToBeListedList",
        "label": "待上市",
    },
    "recently_listed": {
        "url": "https://ipo.jinwucj.com/api/makeNew/listedV",
        "label": "最新上市",
    },
    "filed_passed_hearing": {
        "url": "https://ipo.jinwucj.com/api/makeNew/getTableDataByStatus",
        "label": "已递表-通过聆讯",
        "body": {"status": 1, "pageNum": 1, "pageSize": 5},
    },
    "filed_latest": {
        "url": "https://ipo.jinwucj.com/api/makeNew/getTableDataByStatus",
        "label": "已递表-最新递表",
        "body": {"status": 0, "pageNum": 1, "pageSize": 5},
    },
}

DETAIL_ENDPOINTS = {
    "offering_details": {
        "url": "https://ipo.jinwucj.com/api/offeringDetails/getOfferingDetails",
        "label": "招股详情",
    },
    "margin_info": {
        "url": "https://ipo.jinwucj.com/api/offeringDetails/getMarginInfo",
        "label": "融资认购动态",
    },
    "broker_info": {
        "url": "https://ipo.jinwucj.com/api/offeringDetails/getBrokerInfo",
        "label": "券商融资认购",
    },
    "company_profile": {
        "url": "https://ipo.jinwucj.com/api/offeringDetails/getCompanyProfile",
        "label": "公司概况",
    },
    "placement_basic": {
        "url": "https://ipo.jinwucj.com/api/offeringDetails/getCompanyInfoByCode",
        "label": "配售结果-基本信息",
    },
    "placement_other": {
        "url": "https://ipo.jinwucj.com/api/offeringDetails/getOtherInfoByCode",
        "label": "配售结果-其他信息",
    },
    "placement_detail": {
        "url": "https://ipo.jinwucj.com/api/offeringDetails/getPublicOfferingByCode",
        "label": "配售结果",
    },
}


class HkIpoScraper(BaseScraper):
    """Hong Kong IPO data scraper from jinwucj.com (金吾财经)."""

    meta = ScraperMeta(
        id="hk_ipo",
        name="港股IPO数据",
        version="0.1.0",
        description="抓取金吾财经港股IPO数据：认购、上市、递表、招股详情、融资、配售结果",
        author="crawlcraft",
        topics=["hk-ipo"],
    )

    async def fetch(self, ctx: ScrapeContext) -> ScrapeResult:
        """Fetch IPO data based on task configuration.

        Config options:
        - mode: "list" (default, fetch IPO lists) or "detail" (fetch IPO details)
        - endpoints: list of endpoint keys to call (default: all list endpoints)
        - stock_codes: list of stock codes for detail mode (e.g. ["02723.hk"])
        """
        import httpx

        config = ctx.config
        mode = config.get("mode", "list")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            if mode == "list":
                return await self._fetch_lists(client, config)
            elif mode == "detail":
                return await self._fetch_details(client, config)
            else:
                return ScrapeResult(success=False, error=f"Unknown mode: {mode}")

    async def _fetch_lists(self, client, config) -> ScrapeResult:
        """Fetch IPO list endpoints."""
        endpoint_keys = config.get(
            "endpoints",
            list(ENDPOINTS.keys()),
        )
        results = []

        for key in endpoint_keys:
            ep = ENDPOINTS.get(key)
            if not ep:
                continue

            try:
                body = ep.get("body", {})
                resp = await client.post(ep["url"], json=body)
                resp.raise_for_status()
                data = resp.json()

                results.append({
                    "endpoint": key,
                    "label": ep["label"],
                    "code": data.get("code"),
                    "count": self._count_items(data),
                    "items": data.get("body", data),
                })
            except Exception as exc:
                results.append({
                    "endpoint": key,
                    "label": ep["label"],
                    "error": str(exc),
                })

        return ScrapeResult(success=True, data=results)

    async def _fetch_details(self, client, config) -> ScrapeResult:
        """Fetch IPO details for specific stock codes."""
        stock_codes = config.get("stock_codes", [])
        if not stock_codes:
            return ScrapeResult(success=False, error="No stock_codes provided for detail mode")

        endpoint_keys = config.get(
            "endpoints",
            list(DETAIL_ENDPOINTS.keys()),
        )
        results = []

        for code in stock_codes:
            for key in endpoint_keys:
                ep = DETAIL_ENDPOINTS.get(key)
                if not ep:
                    continue

                try:
                    resp = await client.post(ep["url"], json={"code": code})
                    resp.raise_for_status()
                    data = resp.json()

                    results.append({
                        "stock_code": code,
                        "endpoint": key,
                        "label": ep["label"],
                        "code": data.get("code"),
                        "data": data.get("body"),
                    })
                except Exception as exc:
                    results.append({
                        "stock_code": code,
                        "endpoint": key,
                        "label": ep["label"],
                        "error": str(exc),
                    })

        return ScrapeResult(success=True, data=results)

    @staticmethod
    def _count_items(data: dict) -> int:
        """Count items in a list response."""
        body = data.get("body", {})
        if isinstance(body, list):
            return len(body)
        if isinstance(body, dict):
            lst = body.get("list", [])
            return len(lst) if isinstance(lst, list) else 0
        return 0

    def validate_config(self, config: dict) -> bool:
        """Validate plugin configuration."""
        if not isinstance(config, dict):
            return False
        mode = config.get("mode", "list")
        if mode not in ("list", "detail"):
            return False
        if mode == "detail" and not config.get("stock_codes"):
            return False
        return True
