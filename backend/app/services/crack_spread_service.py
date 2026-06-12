"""
Crack Spread Analytics Service
================================
Computes and persists the 3:2:1 refinery crack spread for WTI and Brent.

Formula:
    crack_spread = (2 * gasoline_bbl + 1 * distillate_bbl - 3 * crude) / 3

Unit conversions:
    RBOB Gasoline (RB=F) is quoted in USD/gallon → × 42 to get USD/bbl
    Heating Oil / ULSD (HO=F) is quoted in USD/gallon → × 42 to get USD/bbl
    WTI (CL=F) and Brent (BZ=F) are quoted in USD/bbl (no conversion)
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.crack_spread import CrackSpread

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GALLONS_PER_BARREL = 42.0

CRUDE_TICKERS = {
    "wti": "CL=F",
    "brent": "BZ=F",
}

PRODUCT_TICKERS = {
    "gasoline": "RB=F",     # RBOB, $/gallon
    "distillate": "HO=F",   # Heating Oil/ULSD, $/gallon
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_ohlcv(ticker_symbol: str, period: str = "2y") -> pd.Series:
    """Fetch daily close prices for a given yfinance ticker."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=period)
        if hist.empty:
            logger.warning("No data for ticker: %s", ticker_symbol)
            return pd.Series(dtype=float)
        series = hist["Close"].dropna()
        series.index = pd.to_datetime(series.index).normalize()
        return series
    except Exception as exc:
        logger.error("Error fetching %s: %s", ticker_symbol, exc)
        return pd.Series(dtype=float)


def _build_crack_dataframe(crude_series: pd.Series) -> pd.DataFrame:
    """
    Align crude, gasoline, and distillate series on a common date index
    and compute the 3:2:1 crack spread.
    """
    gasoline_raw = _fetch_ohlcv(PRODUCT_TICKERS["gasoline"])
    distillate_raw = _fetch_ohlcv(PRODUCT_TICKERS["distillate"])

    if gasoline_raw.empty or distillate_raw.empty:
        logger.error("Cannot compute crack spread — missing product prices")
        return pd.DataFrame()

    # Convert $/gallon → $/barrel
    gasoline_bbl = gasoline_raw * GALLONS_PER_BARREL
    distillate_bbl = distillate_raw * GALLONS_PER_BARREL

    df = pd.DataFrame(
        {
            "crude": crude_series,
            "gasoline": gasoline_bbl,
            "distillate": distillate_bbl,
        }
    ).dropna()

    if df.empty:
        return df

    # 3:2:1 crack spread
    df["crack_spread"] = (
        (2 * df["gasoline"] + 1 * df["distillate"] - 3 * df["crude"]) / 3
    ).round(4)

    return df


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def compute_and_store_crack_spreads(db: Session) -> Dict[str, int]:
    """
    Fetch WTI, Brent, RBOB, and Heating Oil price histories.
    Compute 3:2:1 crack spread for both crude types.
    Upsert into crack_spreads table.

    Returns a summary dict like {"wti": 252, "brent": 252}.
    """
    summary: Dict[str, int] = {}

    # Fetch product prices once (shared between WTI and Brent cracks)
    gasoline_raw = _fetch_ohlcv(PRODUCT_TICKERS["gasoline"])
    distillate_raw = _fetch_ohlcv(PRODUCT_TICKERS["distillate"])

    if gasoline_raw.empty or distillate_raw.empty:
        logger.error("Missing product prices — aborting crack spread computation")
        return summary

    gasoline_bbl = gasoline_raw * GALLONS_PER_BARREL
    distillate_bbl = distillate_raw * GALLONS_PER_BARREL

    for crude_type, ticker in CRUDE_TICKERS.items():
        logger.info("Computing crack spread for %s", crude_type)
        crude_series = _fetch_ohlcv(ticker)

        if crude_series.empty:
            logger.warning("Skipping %s — no crude price data", crude_type)
            continue

        df = pd.DataFrame(
            {
                "crude": crude_series,
                "gasoline": gasoline_bbl,
                "distillate": distillate_bbl,
            }
        ).dropna()

        if df.empty:
            continue

        df["crack_spread"] = (
            (2 * df["gasoline"] + 1 * df["distillate"] - 3 * df["crude"]) / 3
        ).round(4)

        rows_upserted = 0
        try:
            for date_idx, row in df.iterrows():
                ts = datetime(
                    date_idx.year, date_idx.month, date_idx.day,
                    tzinfo=timezone.utc
                )
                existing = (
                    db.query(CrackSpread)
                    .filter(
                        and_(
                            CrackSpread.crude_type == crude_type,
                            CrackSpread.timestamp == ts,
                        )
                    )
                    .first()
                )

                if existing:
                    existing.crude_price = float(row["crude"])
                    existing.gasoline_price = float(row["gasoline"])
                    existing.distillate_price = float(row["distillate"])
                    existing.crack_spread = float(row["crack_spread"])
                else:
                    db.add(
                        CrackSpread(
                            crude_type=crude_type,
                            crude_price=float(row["crude"]),
                            gasoline_price=float(row["gasoline"]),
                            distillate_price=float(row["distillate"]),
                            crack_spread=float(row["crack_spread"]),
                            timestamp=ts,
                        )
                    )
                rows_upserted += 1

            db.commit()
            summary[crude_type] = rows_upserted
            logger.info("Upserted %d crack spread rows for %s", rows_upserted, crude_type)

        except Exception as exc:
            logger.error("Error persisting crack spreads for %s: %s", crude_type, exc)
            db.rollback()

    return summary


def latest_crack(db: Session, crude_type: str = "wti") -> Optional[Dict[str, Any]]:
    """Return the most recent crack spread record for the given crude type."""
    record = (
        db.query(CrackSpread)
        .filter(CrackSpread.crude_type == crude_type.lower())
        .order_by(CrackSpread.timestamp.desc())
        .first()
    )
    if not record:
        return None
    return _record_to_dict(record)


def crack_history(
    db: Session,
    crude_type: str = "wti",
    days: int = 365,
) -> List[Dict[str, Any]]:
    """Return crack spread history for the given crude type (ascending order)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    records = (
        db.query(CrackSpread)
        .filter(
            CrackSpread.crude_type == crude_type.lower(),
            CrackSpread.timestamp >= cutoff,
        )
        .order_by(CrackSpread.timestamp.asc())
        .all()
    )
    return [_record_to_dict(r) for r in records]


def crack_statistics(
    db: Session,
    crude_type: str = "wti",
) -> Dict[str, Any]:
    """
    Compute summary statistics for a given crude type's crack spread:
    latest, avg_30d, avg_90d, volatility, trend (positive/negative/neutral).
    """
    records_90 = (
        db.query(CrackSpread)
        .filter(
            CrackSpread.crude_type == crude_type.lower(),
            CrackSpread.timestamp >= datetime.now(timezone.utc) - timedelta(days=90),
        )
        .order_by(CrackSpread.timestamp.desc())
        .all()
    )

    if not records_90:
        return _empty_crack_stats(crude_type)

    all_vals = [r.crack_spread for r in records_90]  # newest first
    vals_30 = all_vals[:30]

    latest_val = all_vals[0]
    avg_30d = round(float(np.mean(vals_30)), 4) if vals_30 else None
    avg_90d = round(float(np.mean(all_vals)), 4)
    vol = round(float(np.std(all_vals, ddof=1)), 4) if len(all_vals) > 1 else 0.0

    # Simple linear trend on last 30 days
    trend = "neutral"
    if len(vals_30) >= 5:
        recent_mean = float(np.mean(vals_30[:5]))     # last 5 days
        older_mean = float(np.mean(vals_30[-5:]))     # 25-30 days ago
        if recent_mean > older_mean * 1.01:
            trend = "positive"
        elif recent_mean < older_mean * 0.99:
            trend = "negative"

    return {
        "crude_type": crude_type.lower(),
        "latest": round(latest_val, 4),
        "avg_30d": avg_30d,
        "avg_90d": avg_90d,
        "volatility": vol,
        "trend": trend,
        "sample_size": len(records_90),
        "as_of": records_90[0].timestamp.isoformat(),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record_to_dict(r: CrackSpread) -> Dict[str, Any]:
    return {
        "id": r.id,
        "crude_type": r.crude_type,
        "crude_price": r.crude_price,
        "gasoline_price": r.gasoline_price,
        "distillate_price": r.distillate_price,
        "crack_spread": r.crack_spread,
        "timestamp": r.timestamp.isoformat(),
    }


def _empty_crack_stats(crude_type: str) -> Dict[str, Any]:
    return {
        "crude_type": crude_type.lower(),
        "latest": None,
        "avg_30d": None,
        "avg_90d": None,
        "volatility": None,
        "trend": None,
        "sample_size": 0,
        "as_of": None,
    }
