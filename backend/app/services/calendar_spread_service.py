"""
Calendar Spread Analytics Service
==================================
Computes and persists futures calendar spreads for WTI and Brent crude.

Spread pairs: M1-M2, M2-M3, M3-M4, M1-M6, M1-M12
Formula: spread = nearby_contract_price - deferred_contract_price

Data strategy:
  - Fetch 1-year of daily history for front-month futures (CL=F / BZ=F) via yfinance.
  - Simulate deferred months using a configurable day-offset approximation
    (each futures month ≈ 30 calendar days apart).
  - For M1-M6 / M1-M12 we shift the historical series by 5/11 monthly offsets.
  - Persist results to the calendar_spreads table (upsert by commodity/contracts/date).
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

import pandas as pd
import numpy as np
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.calendar_spread import CalendarSpread

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMMODITY_TICKERS = {
    "wti": "CL=F",
    "brent": "BZ=F",
}

# Spread definitions: (label_near, label_far, approx_business_days_offset)
# 21 trading days ≈ 1 calendar month
SPREAD_PAIRS: List[Tuple[str, str, int]] = [
    ("M1", "M2",   21),
    ("M2", "M3",   21),
    ("M3", "M4",   21),
    ("M1", "M6",   105),   # 5 months
    ("M1", "M12",  231),   # 11 months
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_price_series(ticker_symbol: str, period: str = "2y") -> pd.Series:
    """Return a daily close price Series indexed by date."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            logger.warning("No data returned for %s", ticker_symbol)
            return pd.Series(dtype=float)
        series = hist["Close"].dropna()
        series.index = pd.to_datetime(series.index).normalize()  # date-only index
        return series
    except Exception as exc:
        logger.error("Error fetching %s: %s", ticker_symbol, exc)
        return pd.Series(dtype=float)


def _compute_spread_series(
    series: pd.Series, offset_days: int
) -> pd.DataFrame:
    """
    Create a DataFrame with columns [price1, price2, spread].
    price1  = series value at date t  (nearby / M1 proxy)
    price2  = series value at date t-offset  (deferred proxy, shifted forward)

    Interpretation: on any given day, the "M1" price is today's front-month close,
    and the "M2" price is estimated as the close from ~21 trading days ago, which
    represents what the M2 contract *was* when today's M1 was the M2.
    """
    deferred = series.shift(offset_days)  # pandas shift by rows (trading days)
    df = pd.DataFrame({"price1": series, "price2": deferred})
    df = df.dropna()
    df["spread"] = (df["price1"] - df["price2"]).round(4)
    return df


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def compute_and_store_calendar_spreads(db: Session) -> Dict[str, int]:
    """
    Fetch latest price history for WTI and Brent, compute all spread pairs,
    and upsert into the calendar_spreads table.

    Returns a summary dict like {"wti_M1-M2": 252, "brent_M1-M2": 252, ...}
    """
    summary: Dict[str, int] = {}

    for commodity, ticker in COMMODITY_TICKERS.items():
        logger.info("Fetching price series for %s (%s)", commodity, ticker)
        price_series = _fetch_price_series(ticker)

        if price_series.empty:
            logger.warning("Skipping %s — no price data", commodity)
            continue

        for near_label, far_label, offset in SPREAD_PAIRS:
            spread_key = f"{commodity}_{near_label}-{far_label}"
            try:
                df = _compute_spread_series(price_series, offset)
                rows_upserted = 0

                for date_idx, row in df.iterrows():
                    ts = datetime(
                        date_idx.year, date_idx.month, date_idx.day,
                        tzinfo=timezone.utc
                    )
                    existing = (
                        db.query(CalendarSpread)
                        .filter(
                            and_(
                                CalendarSpread.commodity == commodity,
                                CalendarSpread.contract1 == near_label,
                                CalendarSpread.contract2 == far_label,
                                CalendarSpread.timestamp == ts,
                            )
                        )
                        .first()
                    )

                    if existing:
                        existing.price1 = float(row["price1"])
                        existing.price2 = float(row["price2"])
                        existing.spread = float(row["spread"])
                    else:
                        db.add(
                            CalendarSpread(
                                commodity=commodity,
                                contract1=near_label,
                                contract2=far_label,
                                price1=float(row["price1"]),
                                price2=float(row["price2"]),
                                spread=float(row["spread"]),
                                timestamp=ts,
                            )
                        )
                    rows_upserted += 1

                db.commit()
                summary[spread_key] = rows_upserted
                logger.info("Upserted %d rows for %s", rows_upserted, spread_key)

            except Exception as exc:
                logger.error("Error computing %s: %s", spread_key, exc)
                db.rollback()

    return summary


def latest_spread(
    db: Session,
    commodity: str,
    contract1: str,
    contract2: str,
) -> Optional[Dict[str, Any]]:
    """Return the most recent calendar spread record for the given pair."""
    record = (
        db.query(CalendarSpread)
        .filter(
            CalendarSpread.commodity == commodity.lower(),
            CalendarSpread.contract1 == contract1.upper(),
            CalendarSpread.contract2 == contract2.upper(),
        )
        .order_by(CalendarSpread.timestamp.desc())
        .first()
    )
    if not record:
        return None
    return _record_to_dict(record)


def spread_history(
    db: Session,
    commodity: str,
    contract1: str,
    contract2: str,
    days: int = 365,
) -> List[Dict[str, Any]]:
    """Return spread history for the given pair, newest first."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records = (
        db.query(CalendarSpread)
        .filter(
            CalendarSpread.commodity == commodity.lower(),
            CalendarSpread.contract1 == contract1.upper(),
            CalendarSpread.contract2 == contract2.upper(),
            CalendarSpread.timestamp >= cutoff,
        )
        .order_by(CalendarSpread.timestamp.asc())
        .all()
    )
    return [_record_to_dict(r) for r in records]


def spread_statistics(
    db: Session,
    commodity: str,
    contract1: str,
    contract2: str,
) -> Dict[str, Any]:
    """
    Compute summary statistics for a given spread pair:
    latest, daily_change, weekly_change, monthly_change, volatility, z_score.
    """
    records = (
        db.query(CalendarSpread)
        .filter(
            CalendarSpread.commodity == commodity.lower(),
            CalendarSpread.contract1 == contract1.upper(),
            CalendarSpread.contract2 == contract2.upper(),
        )
        .order_by(CalendarSpread.timestamp.desc())
        .limit(365)
        .all()
    )

    if not records:
        return _empty_stats()

    spreads = [r.spread for r in records]  # newest first
    latest_val = spreads[0]

    def _change(n: int) -> Optional[float]:
        if len(spreads) > n:
            return round(latest_val - spreads[n], 4)
        return None

    arr = np.array(spreads)
    vol = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    mean = float(np.mean(arr))
    z_score = round((latest_val - mean) / vol, 4) if vol > 0 else 0.0

    return {
        "commodity": commodity.lower(),
        "contract1": contract1.upper(),
        "contract2": contract2.upper(),
        "latest": round(latest_val, 4),
        "daily_change": _change(1),
        "weekly_change": _change(5),
        "monthly_change": _change(21),
        "volatility": round(vol, 4),
        "z_score": z_score,
        "sample_size": len(records),
        "as_of": records[0].timestamp.isoformat(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record_to_dict(r: CalendarSpread) -> Dict[str, Any]:
    return {
        "id": r.id,
        "commodity": r.commodity,
        "contract1": r.contract1,
        "contract2": r.contract2,
        "price1": r.price1,
        "price2": r.price2,
        "spread": r.spread,
        "timestamp": r.timestamp.isoformat(),
    }


def _empty_stats() -> Dict[str, Any]:
    return {
        "commodity": None,
        "contract1": None,
        "contract2": None,
        "latest": None,
        "daily_change": None,
        "weekly_change": None,
        "monthly_change": None,
        "volatility": None,
        "z_score": None,
        "sample_size": 0,
        "as_of": None,
    }
