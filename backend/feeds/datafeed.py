"""
Oil Trading Desk — Yahoo Finance Data Feed

Fetches prices, history, and futures curve via yfinance.
All functions are designed to run in an asyncio executor since
yfinance is a synchronous library.

Tickers:
  CL=F  (WTI Crude)
  BZ=F  (Brent Crude)
  RB=F  (RBOB Gasoline)
  HO=F  (Heating Oil)
  DX-Y.NYB (US Dollar Index)
  CLF-CLZ + year suffix (12-month NYMEX curve)
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from hub import hub
from utils.helpers import safe_float

logger = logging.getLogger("otd.feeds.datafeed")

# ── Ticker map ────────────────────────────────────────────────
SPOT_TICKERS = {
    "wti": "CL=F",
    "brent": "BZ=F",
    "rbob": "RB=F",
    "heatingOil": "HO=F",
    "dxy": "DX-Y.NYB",
}

INSTRUMENT_META = {
    "brent": {"name": "Brent Crude", "exchange": "ICE", "unit": "$/bbl", "decimals": 2},
    "wti": {"name": "WTI Crude", "exchange": "NYMEX", "unit": "$/bbl", "decimals": 2},
    "gasoil": {"name": "Gasoil", "exchange": "ICE", "unit": "$/mt", "decimals": 2},
    "heatingOil": {"name": "Heating Oil", "exchange": "NYMEX", "unit": "$/gal", "decimals": 4},
    "rbob": {"name": "RBOB Gasoline", "exchange": "NYMEX", "unit": "$/gal", "decimals": 4},
}

# NYMEX contract month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun,
# N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
MONTH_CODES = "FGHJKMNQUVXZ"


def _get_curve_tickers() -> list[str]:
    """Generate 12 monthly NYMEX WTI futures tickers from the current month."""
    now = datetime.now()
    tickers = []
    for i in range(12):
        target = now + timedelta(days=30 * (i + 1))
        month_idx = target.month - 1
        code = MONTH_CODES[month_idx]
        year_suffix = str(target.year)[-2:]
        tickers.append(f"CL{code}{year_suffix}.NYM")
    return tickers


def _fetch_spot_prices_sync() -> dict:
    """Synchronous: fetch latest spot prices for all tickers."""
    results = {}
    try:
        tickers_str = " ".join(SPOT_TICKERS.values())
        data = yf.download(tickers_str, period="2d", interval="1d", progress=False, group_by="ticker")

        for key, ticker in SPOT_TICKERS.items():
            try:
                if len(SPOT_TICKERS) > 1 and ticker in data.columns.get_level_values(0):
                    df = data[ticker]
                else:
                    df = data

                if df.empty or len(df) < 1:
                    continue

                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]

                close = safe_float(latest.get("Close"))
                prev_close = safe_float(prev.get("Close"))
                change = round(close - prev_close, 4)
                change_pct = round((change / prev_close * 100) if prev_close else 0, 2)

                results[key] = {
                    "price": round(close, 4),
                    "change": change,
                    "changePercent": change_pct,
                    "high": round(safe_float(latest.get("High")), 4),
                    "low": round(safe_float(latest.get("Low")), 4),
                    "volume": int(safe_float(latest.get("Volume"))),
                    "openInterest": 0,
                }
            except Exception as e:
                logger.warning(f"Failed to parse {key}/{ticker}: {e}")

    except Exception as e:
        logger.error(f"yfinance spot download failed: {e}")

    return results


def _fetch_history_sync(period: str = "1y") -> dict:
    """Synchronous: fetch 1-year daily OHLCV for all instruments."""
    results = {}
    for key, ticker in SPOT_TICKERS.items():
        if key == "dxy":
            continue  # DXY history handled separately
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False)
            if df.empty:
                continue

            records = []
            for idx, row in df.iterrows():
                date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
                records.append({
                    "date": date_str,
                    "timestamp": int(idx.timestamp() * 1000) if hasattr(idx, "timestamp") else 0,
                    "open": round(safe_float(row.get("Open")), 4),
                    "high": round(safe_float(row.get("High")), 4),
                    "low": round(safe_float(row.get("Low")), 4),
                    "close": round(safe_float(row.get("Close")), 4),
                    "volume": int(safe_float(row.get("Volume"))),
                })
            results[key] = records
        except Exception as e:
            logger.warning(f"History fetch failed for {key}: {e}")

    return results


def _fetch_curve_sync() -> list:
    """Synchronous: fetch 12-month NYMEX WTI futures curve."""
    tickers = _get_curve_tickers()
    curve = []
    try:
        tickers_str = " ".join(tickers)
        data = yf.download(tickers_str, period="1d", interval="1d", progress=False, group_by="ticker")

        for ticker in tickers:
            try:
                if ticker in data.columns.get_level_values(0):
                    df = data[ticker]
                else:
                    df = data

                if df.empty:
                    continue

                close = safe_float(df.iloc[-1].get("Close"))
                if close > 0:
                    curve.append({
                        "month": ticker.replace(".NYM", ""),
                        "price": round(close, 2),
                    })
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Curve fetch failed: {e}")

    return curve


def _fetch_5y_same_week_sync() -> dict:
    """Synchronous: fetch 5-year WTI weekly closes for current-week range."""
    try:
        df = yf.download("CL=F", period="5y", interval="1wk", progress=False)
        if df.empty:
            return {}

        current_week = datetime.now().isocalendar()[1]
        weekly_data = []

        for idx, row in df.iterrows():
            week_num = idx.isocalendar()[1] if hasattr(idx, "isocalendar") else 0
            close = safe_float(row.get("Close"))
            if close > 0:
                weekly_data.append({"week": week_num, "close": close, "year": idx.year if hasattr(idx, "year") else 0})

        # Filter to same week of year
        same_week = [d for d in weekly_data if d["week"] == current_week]
        if not same_week:
            return {}

        closes = [d["close"] for d in same_week]
        return {
            "week": current_week,
            "min": round(min(closes), 2),
            "max": round(max(closes), 2),
            "mean": round(sum(closes) / len(closes), 2),
            "years": len(closes),
        }
    except Exception as e:
        logger.warning(f"5-year same-week fetch failed: {e}")
        return {}


# ── Async wrappers (yfinance is synchronous) ──────────────────

async def fetch_prices():
    """Fetch latest spot prices and update hub."""
    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, _fetch_spot_prices_sync)
        if results:
            hub.prices = results
            # Update DXY from yfinance as fallback
            if "dxy" in results and hub.dxy_source != "twelvedata":
                hub.dxy_value = results["dxy"]["price"]
                hub.dxy_change = results["dxy"]["change"]
                hub.dxy_source = "yfinance"
            hub.update_feed_status("yfinance", True)
            logger.info(f"Prices updated: {len(results)} instruments")
        else:
            hub.update_feed_status("yfinance", False, "No data returned", synthetic=True)
    except Exception as e:
        hub.update_feed_status("yfinance", False, str(e))
        logger.error(f"Price fetch error: {e}")


async def fetch_history():
    """Fetch 1-year price history and update hub."""
    loop = asyncio.get_event_loop()
    try:
        results = await loop.run_in_executor(None, _fetch_history_sync)
        if results:
            hub.price_history = results
            logger.info(f"History updated: {list(results.keys())}")
    except Exception as e:
        logger.error(f"History fetch error: {e}")


async def fetch_curve():
    """Fetch 12-month NYMEX futures curve and update hub."""
    loop = asyncio.get_event_loop()
    try:
        curve = await loop.run_in_executor(None, _fetch_curve_sync)
        if curve:
            hub.curve = curve
            hub.curve_history.append({"time": time.time(), "curve": curve})
            logger.info(f"Curve updated: {len(curve)} contracts")
    except Exception as e:
        logger.error(f"Curve fetch error: {e}")


async def fetch_5y_same_week():
    """Fetch 5-year same-week WTI range and update hub."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _fetch_5y_same_week_sync)
        if result:
            hub.five_year_range = result
            logger.info(f"5-year range: week {result.get('week')}, ${result.get('min')}-${result.get('max')}")
    except Exception as e:
        logger.error(f"5-year range fetch error: {e}")


async def bootstrap():
    """
    Initial data load at startup.
    Fetches prices, history, curve, and 5-year range.
    """
    logger.info("Bootstrapping Yahoo Finance data...")
    await fetch_prices()
    await fetch_history()
    await fetch_curve()
    await fetch_5y_same_week()
    logger.info("Yahoo Finance bootstrap complete.")
