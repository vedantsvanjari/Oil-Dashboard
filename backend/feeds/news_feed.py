"""
Oil Trading Desk — RSS News Aggregation Feed

Aggregates oil & energy news from 4 RSS sources + 3 Google News analyst feeds.
Each headline is scored with VADER sentiment.

Sources:
  1. OilPrice.com main RSS
  2. Google News: "crude+oil+price"
  3. Google News: "WTI+OPEC+brent"
  4. Hellenic Shipping News RSS

Analyst feeds (15-min cadence):
  1. Google News: "Amena Bakr"
  2. Google News: "Javier Blas"
  3. Google News: "Trump+oil"

3-layer stale-news defense:
  - pubDate cap (6 hours max age)
  - URL date regex (reject URLs with old dates)
  - Headline year regex (reject headlines mentioning past years)
"""

import re
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from collections import deque

import httpx
import feedparser

from hub import hub
from feeds.sentiment import score_headline

logger = logging.getLogger("otd.feeds.news")

# ── RSS feed URLs ─────────────────────────────────────────────
RSS_FEEDS = [
    {
        "name": "OilPrice",
        "url": "https://oilprice.com/rss/main",
        "category": "Markets",
    },
    {
        "name": "Google News",
        "url": "https://news.google.com/rss/search?q=crude+oil+price&hl=en-US&gl=US&ceid=US:en",
        "category": "Markets",
    },
    {
        "name": "Google News",
        "url": "https://news.google.com/rss/search?q=WTI+OPEC+brent&hl=en-US&gl=US&ceid=US:en",
        "category": "OPEC",
    },
    {
        "name": "Hellenic Shipping",
        "url": "https://www.hellenicshippingnews.com/feed/",
        "category": "Tankers",
    },
]

ANALYST_FEEDS = [
    {
        "name": "Amena Bakr",
        "url": "https://news.google.com/rss/search?q=Amena+Bakr&hl=en-US&gl=US&ceid=US:en",
        "category": "Analyst",
    },
    {
        "name": "Javier Blas",
        "url": "https://news.google.com/rss/search?q=Javier+Blas&hl=en-US&gl=US&ceid=US:en",
        "category": "Analyst",
    },
    {
        "name": "Trump + Oil",
        "url": "https://news.google.com/rss/search?q=Trump+oil&hl=en-US&gl=US&ceid=US:en",
        "category": "Geopolitics",
    },
]

# ── Stale-news defense constants ──────────────────────────────
MAX_AGE_HOURS = 6
# Regex to find dates in URLs (e.g., /2024/01/15/ or /20240115/)
URL_DATE_PATTERN = re.compile(r"/(\d{4})[/-]?(\d{2})[/-]?(\d{2})/")
# Regex to find years in headlines
HEADLINE_YEAR_PATTERN = re.compile(r"\b(20[12]\d)\b")

# Track seen headline hashes to avoid duplicates
_seen_hashes: set[str] = set()


def _headline_hash(headline: str) -> str:
    """Generate a short hash for deduplication."""
    return hashlib.md5(headline.strip().lower().encode()).hexdigest()[:12]


def _is_stale(entry: dict) -> bool:
    """
    3-layer stale-news defense.
    Returns True if the article should be rejected.
    """
    now = datetime.now(timezone.utc)

    # Layer 1: pubDate cap
    published = entry.get("published_parsed")
    if published:
        try:
            from time import mktime
            pub_dt = datetime.fromtimestamp(mktime(published), tz=timezone.utc)
            if (now - pub_dt) > timedelta(hours=MAX_AGE_HOURS):
                return True
        except (ValueError, OverflowError, TypeError):
            pass

    # Layer 2: URL date regex
    link = entry.get("link", "")
    url_match = URL_DATE_PATTERN.search(link)
    if url_match:
        try:
            url_date = datetime(
                int(url_match.group(1)),
                int(url_match.group(2)),
                int(url_match.group(3)),
                tzinfo=timezone.utc,
            )
            if (now - url_date) > timedelta(hours=MAX_AGE_HOURS * 4):
                return True
        except ValueError:
            pass

    # Layer 3: Headline year regex (reject old-year mentions)
    title = entry.get("title", "")
    year_matches = HEADLINE_YEAR_PATTERN.findall(title)
    current_year = now.year
    for year_str in year_matches:
        if int(year_str) < current_year - 1:
            return True

    return False


def _categorize(title: str, default: str) -> str:
    """Auto-categorize a headline based on keywords."""
    title_lower = title.lower()
    if any(w in title_lower for w in ["opec", "saudi", "quota", "compliance"]):
        return "OPEC"
    if any(w in title_lower for w in ["sanction", "iran", "russia", "war", "attack", "houthi", "red sea", "geopolit"]):
        return "Geopolitics"
    if any(w in title_lower for w in ["inventory", "stockpile", "eia", "draw", "build", "crude stocks"]):
        return "Inventories"
    if any(w in title_lower for w in ["tanker", "shipping", "vlcc", "freight", "vessel"]):
        return "Tankers"
    if any(w in title_lower for w in ["refiner", "refinery", "crack", "gasoline", "diesel"]):
        return "Refineries"
    if any(w in title_lower for w in ["gdp", "fed", "recession", "demand", "china", "india", "dollar", "dxy"]):
        return "Macro"
    return default


def _estimate_impact(sentiment_result: dict, category: str) -> int:
    """Estimate news impact score (1-10) from sentiment strength and category."""
    compound = abs(sentiment_result["compound"])
    base = int(compound * 8) + 3  # 3-11 range
    # Boost for high-impact categories
    if category in ("OPEC", "Geopolitics"):
        base += 1
    return min(10, max(1, base))


async def _fetch_feed(client: httpx.AsyncClient, feed_config: dict) -> list[dict]:
    """Fetch and parse a single RSS feed, returning news items."""
    items = []
    try:
        resp = await client.get(
            feed_config["url"],
            timeout=10.0,
            headers={"User-Agent": "OilTradingDesk/1.0"},
        )
        resp.raise_for_status()

        parsed = feedparser.parse(resp.text)

        for entry in parsed.entries[:15]:  # Max 15 items per feed
            title = entry.get("title", "").strip()
            if not title:
                continue

            # Deduplication
            h = _headline_hash(title)
            if h in _seen_hashes:
                continue

            # Stale check
            if _is_stale(entry):
                continue

            _seen_hashes.add(h)

            # Sentiment scoring
            sentiment_result = score_headline(title)

            # Auto-categorize
            category = _categorize(title, feed_config.get("category", "Markets"))

            # Parse timestamp
            published = entry.get("published_parsed")
            if published:
                try:
                    from time import mktime
                    ts = datetime.fromtimestamp(mktime(published), tz=timezone.utc)
                    timestamp = ts.isoformat()
                except (ValueError, OverflowError, TypeError):
                    timestamp = datetime.now(timezone.utc).isoformat()
            else:
                timestamp = datetime.now(timezone.utc).isoformat()

            # Build summary from description if available
            summary = entry.get("summary", entry.get("description", ""))
            if summary:
                # Strip HTML tags
                summary = re.sub(r"<[^>]+>", "", summary).strip()[:300]

            items.append({
                "headline": title,
                "source": feed_config["name"],
                "category": category,
                "sentiment": sentiment_result["signal"],
                "sentimentScore": sentiment_result["compound"],
                "timestamp": timestamp,
                "impactScore": _estimate_impact(sentiment_result, category),
                "summary": summary,
                "link": entry.get("link", ""),
                "pinned": False,
            })

    except Exception as e:
        logger.warning(f"RSS feed {feed_config['name']} ({feed_config['url'][:50]}...) failed: {e}")

    return items


async def fetch_news():
    """
    Fetch all 4 RSS feeds concurrently and update hub.news.
    Items are sorted by timestamp (newest first), capped at 60.
    """
    async with httpx.AsyncClient() as client:
        try:
            all_items = []
            for feed in RSS_FEEDS:
                items = await _fetch_feed(client, feed)
                all_items.extend(items)

            if all_items:
                # Sort by timestamp descending
                all_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

                # Add to hub deque (auto-caps at 60)
                for item in all_items:
                    # Check if already in hub
                    existing = {n.get("headline") for n in hub.news}
                    if item["headline"] not in existing:
                        hub.news.appendleft(item)

                hub.update_feed_status("rss", True)
                logger.info(f"News updated: {len(all_items)} new items from RSS")
            else:
                hub.update_feed_status("rss", True)  # No new items is OK
                logger.debug("No new RSS items")

        except Exception as e:
            hub.update_feed_status("rss", False, str(e))
            logger.error(f"News aggregation error: {e}")


async def fetch_analyst_news():
    """
    Fetch 3 analyst Google News feeds and update hub.analyst_news.
    Runs at 15-min cadence (separate from main RSS).
    """
    async with httpx.AsyncClient() as client:
        try:
            all_items = []
            for feed in ANALYST_FEEDS:
                items = await _fetch_feed(client, feed)
                all_items.extend(items)

            if all_items:
                all_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                hub.analyst_news = all_items[:20]  # Keep top 20
                logger.info(f"Analyst news updated: {len(all_items)} items")

        except Exception as e:
            logger.error(f"Analyst news error: {e}")
