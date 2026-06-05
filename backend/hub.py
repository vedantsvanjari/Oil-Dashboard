"""
Oil Trading Desk — Central State Hub

All data feeds write into this single shared state object.
The snapshot builder reads from it every 2 seconds to assemble the
JSON payload pushed to WebSocket clients.

Thread safety: All writes happen from asyncio tasks on the same event loop,
so no locking is needed. The hub is a plain mutable namespace.
"""

import time
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("otd.hub")


@dataclass
class FeedStatus:
    """Health status for a single data feed."""
    name: str
    healthy: bool = False
    last_update: float = 0.0
    error: str = ""
    synthetic: bool = False  # True if using fallback/synthetic data


@dataclass
class Hub:
    """
    Central in-memory state for the entire dashboard.

    Every field corresponds to a data domain consumed by the frontend.
    Feeds write directly into these fields; the snapshot builder reads them.
    """

    # ── Prices (from datafeed.py) ─────────────────────────────
    # Latest spot prices: {symbol: {price, change, changePercent, high, low, volume, openInterest}}
    prices: dict = field(default_factory=dict)

    # 252-day OHLCV history per instrument: {symbol: [{"date","open","high","low","close","volume"}, ...]}
    price_history: dict = field(default_factory=dict)

    # Intraday 5-min bars per instrument: {symbol: [...]}
    intraday: dict = field(default_factory=dict)

    # ── Futures Curve (from datafeed.py) ──────────────────────
    # 12-month NYMEX settlement curve: [{"month": "CLF25", "price": 78.50}, ...]
    curve: list = field(default_factory=list)
    curve_history: deque = field(default_factory=lambda: deque(maxlen=200))

    # ── DXY (from twelvedata_feed.py or datafeed.py fallback) ─
    dxy_value: float = 0.0
    dxy_change: float = 0.0
    dxy_source: str = "none"  # "twelvedata" or "yfinance"

    # ── EIA Fundamentals (from eia_feed.py) ───────────────────
    # {crude_stocks, cushing, refinery_util, production, gasoline_stocks, rig_count}
    fundamentals: dict = field(default_factory=dict)

    # EIA inventory history: {series_name: [{"date","value","fiveYearAvg","fiveYearMin","fiveYearMax"}, ...]}
    inventory_history: dict = field(default_factory=dict)

    # ── EIA STEO (from steo_feed.py) ──────────────────────────
    # {supply_world, demand_world, supply_opec, supply_nonopec, demand_oecd, demand_nonoecd, balance: [...]}
    steo: dict = field(default_factory=dict)

    # ── CFTC COT (from cot_feed.py) ───────────────────────────
    # {managed_money_long, managed_money_short, net_position, net_change, report_date}
    cot: dict = field(default_factory=dict)

    # ── News (from news_feed.py) ──────────────────────────────
    # Rolling deque of news items: [{headline, source, category, sentiment, timestamp, impactScore, summary}, ...]
    news: deque = field(default_factory=lambda: deque(maxlen=60))

    # Analyst news (separate feed)
    analyst_news: list = field(default_factory=list)

    # ── Hurricanes (from hurricane_feed.py) ───────────────────
    # [{id, name, category, lat, lon, wind_speed, movement}, ...]
    storms: list = field(default_factory=list)

    # ── Derived / Computed ────────────────────────────────────
    # Calendar spreads: [{id, name, value, structure, dayChange, ma20, zScore, percentile, series}, ...]
    spreads: list = field(default_factory=list)
    wti_brent_spread: dict = field(default_factory=dict)
    crack_spread: dict = field(default_factory=dict)

    # Correlation matrices (computed from EWMA)
    spread_correlation: dict = field(default_factory=dict)
    product_correlation: dict = field(default_factory=dict)

    # Regime detection
    regime: dict = field(default_factory=dict)

    # Sentiment engine
    sentiment: dict = field(default_factory=dict)

    # OPEC data (partially live from STEO, partially hardcoded)
    opec: dict = field(default_factory=dict)

    # 5-year same-week range for WTI
    five_year_range: dict = field(default_factory=dict)

    # ── Added State (AIS, Kalman, Seasonality, Paper) ─────────
    tankers: dict = field(default_factory=dict)
    kalman: dict = field(default_factory=dict)
    seasonality: dict = field(default_factory=dict)
    paper: dict = field(default_factory=dict)

    # ── Feed health tracking ──────────────────────────────────
    feed_status: dict = field(default_factory=lambda: {
        "yfinance": FeedStatus(name="Yahoo Finance"),
        "eia": FeedStatus(name="EIA v2 API"),
        "steo": FeedStatus(name="EIA STEO"),
        "cot": FeedStatus(name="CFTC COT"),
        "twelvedata": FeedStatus(name="Twelve Data"),
        "rss": FeedStatus(name="RSS News"),
        "hurricane": FeedStatus(name="NOAA NHC"),
        "ais": FeedStatus(name="AIS Tankers"),
    })

    # ── Global timestamps ─────────────────────────────────────
    boot_time: float = field(default_factory=time.time)
    last_snapshot: float = 0.0

    def update_feed_status(self, feed: str, healthy: bool, error: str = "", synthetic: bool = False):
        """Update the health status of a data feed."""
        if feed in self.feed_status:
            status = self.feed_status[feed]
            status.healthy = healthy
            status.last_update = time.time()
            status.error = error
            status.synthetic = synthetic

    def get_uptime(self) -> float:
        return time.time() - self.boot_time


# ── Singleton instance ────────────────────────────────────────
hub = Hub()
