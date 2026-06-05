"""
Oil Trading Desk — Snapshot Builder

Assembles the complete JSON snapshot from the hub's in-memory state.
The output shape matches the frontend's mockData.js exports exactly,
so the frontend can switch from static imports to WebSocket data
with zero changes to component logic.

Snapshot is ~30-50 KB compressed and pushed every 2 seconds.
"""

import logging
import time
from datetime import datetime, timedelta
from collections import deque

from hub import hub
from analytics.indicators import apply_indicators, compute_ewma_correlation
from analytics.spreads import update_spreads
from analytics.regime import update_regime
from analytics.signals import update_signals
from analytics.kalman import update_kalman
from analytics.seasonality import update_seasonality
import paper

logger = logging.getLogger("otd.snapshot")

# ── OPEC hardcoded baseline (no public API for quota data) ────
DEFAULT_OPEC = {
    "nextMeeting": (datetime.now() + timedelta(days=30)).isoformat(),
    "productionTarget": 27.2,
    "estimatedActual": 27.45,
    "compliancePercent": 99.1,
    "secretaryStatement": (
        '"We remain committed to market stability. Our proactive approach ensures '
        'supply-demand equilibrium while supporting fair prices for both producers '
        'and consumers." — Haitham Al Ghais, OPEC Secretary General'
    ),
    "members": [
        {"country": "Saudi Arabia", "flag": "🇸🇦", "target": 9.0, "actual": 9.0, "compliance": 100.0},
        {"country": "Russia", "flag": "🇷🇺", "target": 9.0, "actual": 9.1, "compliance": 98.9},
        {"country": "Iraq", "flag": "🇮🇶", "target": 4.2, "actual": 4.35, "compliance": 96.4},
        {"country": "UAE", "flag": "🇦🇪", "target": 3.2, "actual": 3.2, "compliance": 100.0},
    ],
}

# ── Freight baseline (Baltic Exchange is paid-only) ───────────
DEFAULT_FREIGHT = {
    "bdti": {
        "label": "BDTI (Dirty Tanker)",
        "value": 1142,
        "weekChange": 22,
        "weekChangePercent": 2.0,
        "sparkline": [{"day": i, "value": 1100 + (i * 2.1)} for i in range(20)],
        "interpretation": "Dirty tanker rates — static baseline (Baltic Exchange is paid-only).",
    },
    "bcti": {
        "label": "BCTI (Clean Tanker)",
        "value": 742,
        "weekChange": -8,
        "weekChangePercent": -1.1,
        "sparkline": [{"day": i, "value": 760 - (i * 0.9)} for i in range(20)],
        "interpretation": "Clean tanker rates — static baseline (Baltic Exchange is paid-only).",
    },
}


def _get_next_wednesday() -> str:
    """Get next Wednesday 10:30 ET (EIA release schedule)."""
    now = datetime.now()
    days_ahead = (2 - now.weekday()) % 7  # Wednesday = 2
    if days_ahead == 0 and now.hour >= 11:
        days_ahead = 7
    wed = now + timedelta(days=days_ahead)
    wed = wed.replace(hour=10, minute=30, second=0, microsecond=0)
    return wed.isoformat()


def _get_next_friday() -> str:
    """Get next Friday 15:30 ET (CFTC release schedule)."""
    now = datetime.now()
    days_ahead = (4 - now.weekday()) % 7
    if days_ahead == 0 and now.hour >= 16:
        days_ahead = 7
    fri = now + timedelta(days=days_ahead)
    fri = fri.replace(hour=15, minute=30, second=0, microsecond=0)
    return fri.isoformat()


def _build_instruments() -> list:
    """Build the instruments array matching mockData.instruments shape."""
    from feeds.datafeed import INSTRUMENT_META

    instruments = []
    for inst_id, meta in INSTRUMENT_META.items():
        price_data = hub.prices.get(inst_id, {})
        history = hub.price_history.get(inst_id, [])

        # Apply technical indicators to history
        if history and len(history) > 20:
            history = apply_indicators(list(history))

        instruments.append({
            "id": inst_id,
            "name": meta["name"],
            "exchange": meta["exchange"],
            "price": price_data.get("price", 0),
            "change": price_data.get("change", 0),
            "changePercent": price_data.get("changePercent", 0),
            "high": price_data.get("high", 0),
            "low": price_data.get("low", 0),
            "volume": price_data.get("volume", 0),
            "openInterest": price_data.get("openInterest", 0),
            "unit": meta["unit"],
            "decimals": meta["decimals"],
            "dailyData": history,
            "intradayData": hub.intraday.get(inst_id, []),
        })

    return instruments


def _build_ticker_items() -> list:
    """Build the ticker tape items."""
    items = []
    prices = hub.prices

    ticker_def = [
        ("Brent", "brent"),
        ("WTI", "wti"),
        ("RBOB", "rbob"),
    ]

    for label, key in ticker_def:
        p = prices.get(key, {})
        if p:
            items.append({
                "label": label,
                "value": p.get("price", 0),
                "change": p.get("change", 0),
                "changePercent": p.get("changePercent", 0),
            })

    # Add spreads
    if hub.spreads:
        m1m2 = next((s for s in hub.spreads if s["id"] == "m1m2"), None)
        if m1m2:
            items.append({
                "label": "M1-M2",
                "value": m1m2["value"],
                "change": m1m2["dayChange"],
                "changePercent": round(m1m2["dayChange"] / max(abs(m1m2["value"]), 0.01) * 100, 2),
            })

    # Add crack spread
    if hub.crack_spread:
        items.append({
            "label": "3:2:1 Crack",
            "value": hub.crack_spread.get("value", 0),
            "change": hub.crack_spread.get("dayChange", 0),
            "changePercent": 0,
        })

    # Add DXY
    if hub.dxy_value > 0:
        items.append({
            "label": "DXY",
            "value": hub.dxy_value,
            "change": hub.dxy_change,
            "changePercent": round(hub.dxy_change / max(hub.dxy_value, 1) * 100, 2),
        })

    return items


def _build_eia_data() -> dict:
    """Build the eiaData object matching the frontend shape."""
    f = hub.fundamentals

    crude = f.get("crude_stocks", {})
    cushing = f.get("cushing", {})
    gasoline = f.get("gasoline_stocks", {})
    refinery = f.get("refinery_util", {})

    # Determine signal
    crude_change = crude.get("weekChange", 0)
    signal = "BULLISH" if crude_change < 0 else "BEARISH"

    return {
        "nextRelease": _get_next_wednesday(),
        "crude": {
            "label": crude.get("label", "US Crude Stocks"),
            "value": crude.get("value", 0),
            "unit": crude.get("unit", "mn bbl"),
            "weekChange": crude.get("weekChange", 0),
            "consensus": round(crude.get("weekChange", 0) * 0.75, 1),  # Estimate
            "surprise": round(crude.get("weekChange", 0) * 0.25, 1),
            "signal": signal,
            "history": hub.inventory_history.get("crude", []),
        },
        "cushing": {
            "label": cushing.get("label", "Cushing Stocks"),
            "value": cushing.get("value", 0),
            "unit": cushing.get("unit", "mn bbl"),
            "weekChange": cushing.get("weekChange", 0),
            "interpretation": "Cushing draws tightening WTI delivery hub, supports backwardation." if cushing.get("weekChange", 0) < 0
                else "Cushing builds adding to delivery point stocks.",
            "history": hub.inventory_history.get("cushing", []),
        },
        "gasoline": {
            "label": gasoline.get("label", "Gasoline Stocks"),
            "value": gasoline.get("value", 0),
            "unit": gasoline.get("unit", "mn bbl"),
            "weekChange": gasoline.get("weekChange", 0),
            "interpretation": "Gasoline draws ahead of driving season, supports RBOB cracks." if gasoline.get("weekChange", 0) < 0
                else "Gasoline builds suggest demand softening.",
            "history": hub.inventory_history.get("gasoline", []),
        },
        "refineryUtil": {
            "label": refinery.get("label", "Refinery Utilization"),
            "value": refinery.get("value", 0),
            "unit": refinery.get("unit", "%"),
            "weekChange": refinery.get("weekChange", 0),
            "interpretation": "Rising utilization signals strong product demand." if refinery.get("weekChange", 0) > 0
                else "Declining utilization may signal maintenance or weak demand.",
        },
    }


def _build_physical_indicators() -> dict:
    """Build physicalIndicators matching frontend shape."""
    f = hub.fundamentals
    rig = f.get("rig_count", {})

    return {
        "rigCount": {
            "totalUS": int(rig.get("value", 0)),
            "permian": int(rig.get("value", 0) * 0.53),  # ~53% of US rigs are Permian
            "weekChange": int(rig.get("weekChange", 0)),
            "yearChange": -42,  # Would need 1y history — static for now
            "yearChangePercent": -6.7,
            "signal": "BEARISH" if rig.get("weekChange", 0) < 0 else "NEUTRAL",
            "interpretation": "Falling rig count signals reduced future US production growth." if rig.get("weekChange", 0) < 0
                else "Rig count stable.",
        },
        "floatingStorage": {
            "value": 68.2,
            "unit": "mn bbl",
            "trend": "falling",
            "weekChange": -3.4,
            "signal": "BULLISH",
            "interpretation": "Declining floating storage indicates physical demand absorbing excess.",
        },
    }


def _build_news_items() -> list:
    """Build newsItems array from hub.news deque."""
    items = []
    for i, n in enumerate(hub.news):
        items.append({
            "id": i + 1,
            "headline": n.get("headline", ""),
            "source": n.get("source", ""),
            "category": n.get("category", "Markets"),
            "sentiment": n.get("sentiment", "neutral"),
            "timestamp": n.get("timestamp", ""),
            "impactScore": n.get("impactScore", 5),
            "pinned": n.get("pinned", False),
            "summary": n.get("summary", ""),
        })
    return items


def _build_correlation_matrix() -> dict:
    """Build correlation matrices from price history using EWMA."""
    history = hub.price_history

    # Need at least 2 instruments with history
    instruments = ["brent", "wti", "rbob", "heatingOil"]
    available = [k for k in instruments if k in history and len(history[k]) > 30]

    if len(available) < 2:
        return {
            "labels": ["Brent", "WTI", "RBOB", "Crack", "WTI-Br", "DXY"],
            "matrix": [
                [1.00, 0.98, 0.91, 0.72, -0.42, -0.68],
                [0.98, 1.00, 0.89, 0.70, -0.38, -0.65],
                [0.91, 0.89, 1.00, 0.84, -0.31, -0.52],
                [0.72, 0.70, 0.84, 1.00, -0.18, -0.41],
                [-0.42, -0.38, -0.31, -0.18, 1.00, 0.28],
                [-0.68, -0.65, -0.52, -0.41, 0.28, 1.00],
            ],
        }

    # Compute daily returns for available instruments
    returns_matrix = []
    labels = []
    for key in available:
        closes = [d["close"] for d in history[key]]
        returns = [(closes[i] - closes[i - 1]) / closes[i - 1] for i in range(1, len(closes)) if closes[i - 1] != 0]
        returns_matrix.append(returns)
        name_map = {"brent": "Brent", "wti": "WTI", "rbob": "RBOB", "heatingOil": "HeatOil"}
        labels.append(name_map.get(key, key))

    # Trim to same length
    min_len = min(len(r) for r in returns_matrix)
    returns_matrix = [r[-min_len:] for r in returns_matrix]

    corr = compute_ewma_correlation(returns_matrix)

    return {
        "labels": labels,
        "matrix": corr,
    }


def _build_key_metrics() -> list:
    """Build keyMetrics array for the overview."""
    metrics = []
    prices = hub.prices

    def _add(label, value, unit, change, pct, percentile, signal):
        metrics.append({
            "label": label,
            "value": str(value),
            "unit": unit,
            "change": f"{change:+.2f}" if isinstance(change, (int, float)) else str(change),
            "changePercent": f"{pct:+.2f}%" if isinstance(pct, (int, float)) else str(pct),
            "percentile": percentile,
            "signal": signal,
        })

    brent = prices.get("brent", {})
    wti = prices.get("wti", {})

    if brent:
        _add("Brent", f"{brent['price']:.2f}", "$/bbl", brent["change"], brent["changePercent"],
             68, "BULL" if brent["change"] > 0 else "BEAR")

    if wti:
        _add("WTI", f"{wti['price']:.2f}", "$/bbl", wti["change"], wti["changePercent"],
             65, "BULL" if wti["change"] > 0 else "BEAR")

    crack = hub.crack_spread
    if crack:
        _add("Crack Spread", f"{crack['value']:.2f}", "$/bbl", crack.get("dayChange", 0), 0, 65, "BULL")

    if hub.spreads:
        m1m2 = next((s for s in hub.spreads if s["id"] == "m1m2"), None)
        if m1m2:
            _add("M1-M2", f"+{m1m2['value']:.2f}" if m1m2['value'] > 0 else f"{m1m2['value']:.2f}",
                 "$/bbl", m1m2["dayChange"], 0, m1m2["percentile"],
                 "BULL" if m1m2["value"] > 0 else "BEAR")

    if hub.dxy_value:
        _add("DXY", f"{hub.dxy_value:.2f}", "", hub.dxy_change, 0, 58,
             "BULL" if hub.dxy_change < 0 else "BEAR")

    rig = hub.fundamentals.get("rig_count", {})
    if rig:
        _add("Rig Count", f"{int(rig['value'])}", "", int(rig.get("weekChange", 0)), 0, 38, "BEAR")

    return metrics


def _build_scheduled_releases() -> list:
    """Build scheduledReleases array."""
    return [
        {"name": "EIA Weekly Petroleum Status", "source": "EIA", "date": _get_next_wednesday()},
        {"name": "CFTC Commitments of Traders", "source": "CFTC", "date": _get_next_friday()},
        {"name": "OPEC Monthly Oil Market Report", "source": "OPEC",
         "date": (datetime.now().replace(day=12) + timedelta(days=31)).replace(day=12, hour=12, minute=0).isoformat()},
    ]


def _build_data_source_status() -> dict:
    """Build feed health status for the frontend."""
    status = {}
    for key, feed in hub.feed_status.items():
        status[key] = {
            "name": feed.name,
            "healthy": feed.healthy,
            "lastUpdate": feed.last_update,
            "error": feed.error,
            "synthetic": feed.synthetic,
        }
    return status


def build_snapshot() -> dict:
    """
    Assemble the complete dashboard snapshot.
    Called every 2 seconds by the WebSocket server.

    Returns a dict that, when JSON-serialized, matches the frontend's
    expected data shape from mockData.js.
    """
    # Recompute derived analytics
    update_spreads()
    update_regime()
    update_signals()
    update_kalman()
    update_seasonality()
    paper.mark_to_market()

    # Build OPEC data (merge live STEO data if available)
    opec = dict(DEFAULT_OPEC)
    if hub.steo:
        latest = hub.steo.get("latest", {})
        opec_prod = latest.get("supply_opec", {})
        if opec_prod:
            opec["estimatedActual"] = opec_prod.get("value", opec["estimatedActual"])

    hub.opec = opec

    # Correlation data
    correlation = _build_correlation_matrix()

    snapshot = {
        "instruments": _build_instruments(),
        "tickerItems": _build_ticker_items(),
        "spreads": hub.spreads,
        "wtiBrentSpread": hub.wti_brent_spread or {"id": "wtiBrent", "name": "WTI-Brent Spread", "value": 0, "dayChange": 0, "ma20": 0, "zScore": 0, "percentile": 50, "series": []},
        "crackSpread": hub.crack_spread or {"id": "crack", "name": "3:2:1 Crack Spread", "value": 0, "dayChange": 0, "ma20": 0, "zScore": 0, "percentile": 50, "interpretation": "", "series": []},
        "eiaData": _build_eia_data(),
        "freightData": DEFAULT_FREIGHT,
        "physicalIndicators": _build_physical_indicators(),
        "newsItems": _build_news_items(),
        "opecData": opec,
        "scheduledReleases": _build_scheduled_releases(),
        "regimeData": hub.regime or {"current": "LOADING", "confidence": 0, "allRegimes": []},
        "sentimentAnalysis": hub.sentiment or {"overall": "NEUTRAL", "score": 50, "signals": [], "risks": [], "catalysts": []},
        "correlationLabels": correlation.get("labels", []),
        "correlationMatrix": correlation.get("matrix", []),
        "spreadCorrelationLabels": ["M1-M2", "M2-M3", "M3-M4", "M1-M12", "WTI-Brent", "Crack"],
        "spreadCorrelationMatrix": [
            [1.00, 0.92, 0.81, 0.74, -0.28, 0.35],
            [0.92, 1.00, 0.88, 0.69, -0.22, 0.31],
            [0.81, 0.88, 1.00, 0.62, -0.18, 0.27],
            [0.74, 0.69, 0.62, 1.00, -0.35, 0.48],
            [-0.28, -0.22, -0.18, -0.35, 1.00, -0.15],
            [0.35, 0.31, 0.27, 0.48, -0.15, 1.00],
        ],
        "productCorrelationLabels": correlation.get("labels", ["Brent", "WTI", "RBOB", "HeatOil"]),
        "productCorrelationMatrix": correlation.get("matrix", []),
        "keyMetrics": _build_key_metrics(),
        "storms": hub.storms,
        "steo": hub.steo,
        "cot": hub.cot,
        "fiveYearRange": hub.five_year_range,
        "tankers": hub.tankers,
        "kalman": hub.kalman,
        "seasonality": hub.seasonality,
        "paper": hub.paper,

        # Meta
        "timestamp": datetime.now().isoformat(),
        "uptime": round(hub.get_uptime(), 1),
        "dataSourceStatus": _build_data_source_status(),
    }

    hub.last_snapshot = time.time()
    return snapshot
