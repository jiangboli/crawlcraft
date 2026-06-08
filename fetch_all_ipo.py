#!/usr/bin/env python3
"""
HK IPO Data Collection Script
Fetches all jinwucj.com API endpoints and logs structured output
with topic definitions compatible with crawlcraft + Redpanda pipeline.

Usage:
    python3 fetch_all_ipo.py
"""

import json
import logging
import sys
from datetime import datetime, timezone

import requests
import urllib3

urllib3.disable_warnings()

# ── Logging setup ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hk-ipo")


# ── Topic definitions ─────────────────────────────────────────────
# Each topic = one data stream in Redpanda
TOPICS = {
    "subscriptions": {
        "id": "crawl.hk-ipo.subscriptions",
        "endpoint": "/api/makeNew/makeNewList",
        "label": "最新认购",
    },
    "pending": {
        "id": "crawl.hk-ipo.pending",
        "endpoint": "/api/makeNew/getToBeListedList",
        "label": "待上市",
    },
    "listed": {
        "id": "crawl.hk-ipo.listed",
        "endpoint": "/api/makeNew/listedV",
        "label": "最新上市",
    },
    "filed_new": {
        "id": "crawl.hk-ipo.filed",
        "endpoint": "/api/makeNew/getTableDataByStatus",
        "label": "最新递表",
        "body": {"status": 0, "pageNum": 1, "pageSize": 5},
    },
    "filed_approved": {
        "id": "crawl.hk-ipo.filed",
        "endpoint": "/api/makeNew/getTableDataByStatus",
        "label": "通过聆讯",
        "body": {"status": 1, "pageNum": 1, "pageSize": 5},
    },
    "offering": {
        "id": "crawl.hk-ipo.offering",
        "endpoint": "/api/offeringDetails/getOfferingDetails",
        "label": "招股详情",
    },
    "margin": {
        "id": "crawl.hk-ipo.margin",
        "endpoint": "/api/offeringDetails/getMarginInfo",
        "label": "融资认购动态",
    },
    "broker": {
        "id": "crawl.hk-ipo.broker",
        "endpoint": "/api/offeringDetails/getBrokerInfo",
        "label": "券商融资排名",
    },
    "profile": {
        "id": "crawl.hk-ipo.profile",
        "endpoint": "/api/offeringDetails/getCompanyProfile",
        "label": "公司概况",
    },
    "placement_basic": {
        "id": "crawl.hk-ipo.placement",
        "endpoint": "/api/offeringDetails/getCompanyInfoByCode",
        "label": "配售结果-基本信息",
    },
    "placement_other": {
        "id": "crawl.hk-ipo.placement",
        "endpoint": "/api/offeringDetails/getOtherInfoByCode",
        "label": "配售结果-股东锁定期",
    },
    "placement_detail": {
        "id": "crawl.hk-ipo.placement",
        "endpoint": "/api/offeringDetails/getPublicOfferingByCode",
        "label": "配售结果-中签分布",
    },
}


def build_message(topic_key: str, endpoint: str, payload: dict, response: dict) -> dict:
    """Build a Redpanda-ready message with metadata envelope."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "meta": {
            "source": "jinwucj.com",
            "topic": TOPICS[topic_key]["id"],
            "endpoint": endpoint,
            "collected_at": now,
            "api_code": response.get("code"),
            "api_status": response.get("msg"),
        },
        "data": response.get("body", response),
    }


def fetch_one(topic_key: str, stock_code: str | None = None) -> dict | None:
    """Fetch a single endpoint and return a Redpanda message envelope."""
    ep = TOPICS[topic_key]
    url = f"https://ipo.jinwucj.com{ep['endpoint']}"
    body = ep.get("body", {})
    if stock_code:
        body["code"] = stock_code

    try:
        r = requests.post(url, json=body, timeout=15, verify=False)
        r.raise_for_status()
        resp = r.json()

        msg = build_message(topic_key, ep["endpoint"], body, resp)
        return msg

    except Exception as e:
        log.error("  ❌ %s (%s): %s", ep["label"], stock_code or "-", e)
        return None


def print_topic(msg: dict, label: str):
    """Pretty-print a topic message."""
    meta = msg["meta"]
    data = msg["data"]
    topic = meta["topic"]

    # Get item count
    if isinstance(data, list):
        count = len(data)
    elif isinstance(data, dict):
        count = len(data.get("list", data))  # fallback
    else:
        count = "?"

    log.info("─── %s", label)
    log.info("  Topic: %s", topic)
    log.info("  Items: %s", count)
    log.info("  Data:  %s", json.dumps(data, ensure_ascii=False, indent=2)[:2000])
    print()


def main():
    log.info("=" * 60)
    log.info("HK IPO Data Collection — %s", datetime.now().isoformat())
    log.info("=" * 60)
    print()

    # ── Phase 1: List endpoints ───────────────────────────────────
    log.info("📋 Phase 1: IPO Lists")
    list_topics = ["subscriptions", "pending", "listed", "filed_new", "filed_approved"]
    for key in list_topics:
        log.info(">>> Fetching %s ...", TOPICS[key]["label"])
        msg = fetch_one(key)
        if msg:
            print_topic(msg, TOPICS[key]["label"])

    # ── Phase 2: Detail endpoints (using codes from subscriptions) ──
    log.info("📋 Phase 2: IPO Details")
    
    # Get stock codes from latest subscription
    sub_msg = fetch_one("subscriptions")
    stock_codes = []
    if sub_msg:
        body = sub_msg["data"]
        if isinstance(body, list):
            stock_codes = [item.get("symbol") for item in body if item.get("symbol")]
    
    if not stock_codes:
        # Fallback: use sample codes from the doc
        stock_codes = ["03388.hk", "02723.hk", "06872.hk", "00901.hk"]
    
    log.info("Stock codes to query: %s", stock_codes)

    detail_topics = ["offering", "margin", "broker", "profile",
                     "placement_basic", "placement_other", "placement_detail"]

    for code in stock_codes:
        log.info("─── Stock: %s ───", code)
        for key in detail_topics:
            msg = fetch_one(key, code)
            if msg:
                print_topic(msg, f"{TOPICS[key]['label']} ({code})")


if __name__ == "__main__":
    main()
