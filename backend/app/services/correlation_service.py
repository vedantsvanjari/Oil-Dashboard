"""
Advanced Correlation Engine
=============================
Computes Pearson correlation matrices for heatmap-ready API responses.

Architecture:
  1. Dataset Registry — dynamically discovers available datasets by querying the DB.
  2. Series Loaders — pull each time series from existing tables.
  3. Alignment — resamples all series to daily frequency, forward-fills gaps.
  4. Matrix Computation — Pearson correlation via pandas DataFrame.corr().
  5. DB Caching — serializes matrix to JSON in correlation_snapshots; stale after 1 hour.

Matrix types:
  - product:   energy commodity prices
  - spread:    calendar spreads + crack spreads + WTI-Brent
  - macro:     macro indicators (DXY, yields, VIX, S&P500)
  - inventory: crude prices vs EIA inventory fundamentals
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import numpy as np
import yfinance as yf
from sqlalchemy.orm import Session

from app.models.prices import Price
from app.models.macro import MacroData
from app.models.inventories import Inventory
from app.models.refineries import RefineryData
from app.models.calendar_spread import CalendarSpread
from app.models.crack_spread import CrackSpread
from app.models.correlation import CorrelationSnapshot

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported windows
# ---------------------------------------------------------------------------

VALID_WINDOWS = {"7D": 7, "30D": 30, "90D": 90, "180D": 180}

# ---------------------------------------------------------------------------
# Matrix group definitions
# Keys MUST match dataset names returned by discover_datasets()
# ---------------------------------------------------------------------------

MATRIX_GROUPS: Dict[str, List[str]] = {
    "product": [
        "brent", "wti", "gasoline", "heating_oil", "dxy", "us10y",
    ],
    "spread": [
        "wti_M1-M2", "wti_M2-M3", "wti_M3-M4", "wti_M1-M12",
        "brent_M1-M2", "wti_brent_spread",
        "crack_wti", "crack_brent",
    ],
    "macro": [
        "wti", "dxy", "us10y", "us2y", "yield_curve", "vix", "sp500",
    ],
    "inventory": [
        "wti", "crude_inv", "gasoline_inv", "distillate_inv",
        "refinery_utilization",
    ],
}

# Frontend-specific matrix groups
FRONTEND_GROUPS: Dict[str, List[str]] = {
    "product": [
        "wti", "brent", "gasoline", "heating_oil"
    ],
    "spreads": [
        "wti_brent_spread",
        "wti_M1-M2", "wti_M2-M3", "wti_M3-M4", "wti_M1-M6", "wti_M1-M12",
        "brent_M1-M2", "brent_M2-M3", "brent_M3-M4", "brent_M1-M6", "brent_M1-M12",
        "crack"  # Frontend expects "crack", mapped to crack_wti internally
    ],
    "macro": [
        "wti", "brent", "dxy", "us10y", "yield_curve"
    ],
}

# Cache TTL: recompute if older than this
CACHE_TTL_SECONDS = 3600  # 1 hour

# ---------------------------------------------------------------------------
# Dataset Registry
# ---------------------------------------------------------------------------

def discover_datasets(db: Session) -> List[Dict[str, Any]]:
    """
    Dynamically discover all available datasets by querying each table.
    Returns a list of dataset descriptors.
    """
    datasets = []

    # ── Price series ──────────────────────────────────────────────────────
    symbols = db.query(Price.symbol).distinct().all()
    for (sym,) in symbols:
        datasets.append({
            "name": sym,
            "category": "energy",
            "source": "prices_table",
            "description": f"{sym.upper()} daily price",
        })

    # ── Macro series ──────────────────────────────────────────────────────
    macro_count = db.query(MacroData).count()
    if macro_count > 0:
        for field in ["dxy", "us10y", "us2y", "yield_curve"]:
            datasets.append({
                "name": field,
                "category": "macro",
                "source": "macro_data_table",
                "description": field.upper(),
            })

    # ── yfinance-only macro (not persisted in DB, fetched on demand) ──────
    for name, desc in [("vix", "CBOE VIX Index"), ("sp500", "S&P 500 Index")]:
        datasets.append({
            "name": name,
            "category": "macro",
            "source": "yfinance_live",
            "description": desc,
        })

    # ── Inventory series ─────────────────────────────────────────────────
    inv_items = db.query(Inventory.item_name).distinct().all()
    for (item,) in inv_items:
        datasets.append({
            "name": f"{item}_inv",
            "category": "fundamentals",
            "source": "inventories_table",
            "description": f"{item.capitalize()} EIA inventory",
        })

    # ── Refinery series ───────────────────────────────────────────────────
    ref_count = db.query(RefineryData).count()
    if ref_count > 0:
        datasets.append({
            "name": "refinery_utilization",
            "category": "fundamentals",
            "source": "refineries_table",
            "description": "Refinery utilization rate (%)",
        })

    # ── Calendar spread series ────────────────────────────────────────────
    cal_pairs = (
        db.query(CalendarSpread.commodity, CalendarSpread.contract1, CalendarSpread.contract2)
        .distinct()
        .all()
    )
    for (comm, c1, c2) in cal_pairs:
        name = f"{comm}_{c1}-{c2}"
        datasets.append({
            "name": name,
            "category": "spreads",
            "source": "calendar_spreads_table",
            "description": f"{comm.upper()} {c1}-{c2} calendar spread",
        })

    # ── Crack spread series ───────────────────────────────────────────────
    crack_types = db.query(CrackSpread.crude_type).distinct().all()
    for (ct,) in crack_types:
        datasets.append({
            "name": f"crack_{ct}",
            "category": "spreads",
            "source": "crack_spreads_table",
            "description": f"3:2:1 crack spread ({ct.upper()})",
        })

    # ── Synthetic WTI-Brent spread ─────────────────────────────────────────
    if any(d["name"] == "brent" for d in datasets) and any(d["name"] == "wti" for d in datasets):
        datasets.append({
            "name": "wti_brent_spread",
            "category": "spreads",
            "source": "computed",
            "description": "WTI minus Brent spread",
        })

    return datasets


# ---------------------------------------------------------------------------
# Series Loaders
# ---------------------------------------------------------------------------

def _load_price_series(db: Session, symbol: str, days: int) -> pd.Series:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(Price.timestamp, Price.price)
        .filter(Price.symbol == symbol, Price.timestamp >= cutoff)
        .order_by(Price.timestamp.asc())
        .all()
    )
    if not rows:
        return pd.Series(dtype=float, name=symbol)
    # BUG FIX 1: Strip timezone → tz-naive so pd.concat works across all sources.
    # BUG FIX 2: Multiple intraday writes produce duplicate dates after .normalize();
    #            group by date and take the last value to deduplicate.
    idx = pd.to_datetime([r.timestamp for r in rows]).normalize().tz_localize(None)
    s = pd.Series([r.price for r in rows], index=idx, name=symbol)
    s = s.groupby(level=0).last()  # deduplicate same-date entries
    return s


def _load_macro_series(db: Session, field: str, days: int) -> pd.Series:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(MacroData.date, getattr(MacroData, field))
        .filter(MacroData.date >= cutoff.date())
        .order_by(MacroData.date.asc())
        .all()
    )
    if not rows:
        return pd.Series(dtype=float)
    idx = pd.to_datetime([r[0] for r in rows])
    return pd.Series([r[1] for r in rows], index=idx, name=field)


def _load_yfinance_series(ticker: str, name: str, days: int) -> pd.Series:
    period = f"{days}d" if days <= 730 else "2y"
    try:
        hist = yf.Ticker(ticker).history(period=period)
        if hist.empty:
            return pd.Series(dtype=float, name=name)
        s = hist["Close"].dropna()
        # BUG FIX 1: yfinance may return tz-aware index; strip to tz-naive.
        idx = pd.to_datetime(s.index).normalize()
        if idx.tz is not None:
            idx = idx.tz_localize(None)
        s = pd.Series(s.values, index=idx, name=name)
        s = s.groupby(level=0).last()  # safety dedup
        return s
    except Exception as exc:
        logger.warning("yfinance fetch failed for %s: %s", ticker, exc)
        return pd.Series(dtype=float, name=name)


def _load_inventory_series(db: Session, item_name: str, days: int) -> pd.Series:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(Inventory.date, Inventory.quantity)
        .filter(Inventory.item_name == item_name, Inventory.date >= cutoff)
        .order_by(Inventory.date.asc())
        .all()
    )
    name = f"{item_name}_inv"
    if not rows:
        return pd.Series(dtype=float, name=name)
    # BUG FIX 1: TIMESTAMPTZ columns come back tz-aware; strip to tz-naive.
    idx = pd.to_datetime([r.date for r in rows]).normalize().tz_localize(None)
    s = pd.Series([r.quantity for r in rows], index=idx, name=name)
    return s.groupby(level=0).last()


def _load_refinery_series(db: Session, field: str, days: int) -> pd.Series:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(RefineryData.date, getattr(RefineryData, field))
        .filter(RefineryData.date >= cutoff)
        .order_by(RefineryData.date.asc())
        .all()
    )
    if not rows:
        return pd.Series(dtype=float, name=field)
    # BUG FIX 1: TIMESTAMPTZ column; strip timezone.
    idx = pd.to_datetime([r[0] for r in rows]).normalize().tz_localize(None)
    s = pd.Series([r[1] for r in rows], index=idx, name=field)
    return s.groupby(level=0).last()


def _load_calendar_spread_series(
    db: Session, commodity: str, c1: str, c2: str, days: int
) -> pd.Series:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(CalendarSpread.timestamp, CalendarSpread.spread)
        .filter(
            CalendarSpread.commodity == commodity,
            CalendarSpread.contract1 == c1,
            CalendarSpread.contract2 == c2,
            CalendarSpread.timestamp >= cutoff,
        )
        .order_by(CalendarSpread.timestamp.asc())
        .all()
    )
    name = f"{commodity}_{c1}-{c2}"
    if not rows:
        return pd.Series(dtype=float, name=name)
    # BUG FIX 1: TIMESTAMPTZ column; strip timezone.
    idx = pd.to_datetime([r.timestamp for r in rows]).normalize().tz_localize(None)
    s = pd.Series([r.spread for r in rows], index=idx, name=name)
    return s.groupby(level=0).last()


def _load_crack_series(db: Session, crude_type: str, days: int) -> pd.Series:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(CrackSpread.timestamp, CrackSpread.crack_spread)
        .filter(
            CrackSpread.crude_type == crude_type,
            CrackSpread.timestamp >= cutoff,
        )
        .order_by(CrackSpread.timestamp.asc())
        .all()
    )
    name = f"crack_{crude_type}"
    if not rows:
        return pd.Series(dtype=float, name=name)
    # BUG FIX 1: TIMESTAMPTZ column; strip timezone.
    idx = pd.to_datetime([r.timestamp for r in rows]).normalize().tz_localize(None)
    s = pd.Series([r.crack_spread for r in rows], index=idx, name=name)
    return s.groupby(level=0).last()


# ---------------------------------------------------------------------------
# Dataset name → Series resolver
# ---------------------------------------------------------------------------

def _resolve_series(db: Session, name: str, days: int) -> pd.Series:
    """Resolve a dataset name to its pd.Series."""
    # Price table symbols
    if name in ("brent", "wti", "gasoline", "heating_oil"):
        return _load_price_series(db, name, days)

    # Macro DB fields
    if name in ("dxy", "us10y", "us2y", "yield_curve"):
        return _load_macro_series(db, name, days)

    # yfinance-only
    if name == "vix":
        return _load_yfinance_series("^VIX", "vix", days)
    if name == "sp500":
        return _load_yfinance_series("^GSPC", "sp500", days)

    # Inventory items
    if name.endswith("_inv"):
        item = name[:-4]  # strip "_inv"
        return _load_inventory_series(db, item, days)

    # Refinery
    if name == "refinery_utilization":
        return _load_refinery_series(db, "refinery_utilization", days)

    # Calendar spreads  e.g. "wti_M1-M2"
    if "_M" in name:
        parts = name.split("_", 1)
        commodity = parts[0]
        contracts = parts[1].split("-")
        if len(contracts) == 2:
            return _load_calendar_spread_series(db, commodity, contracts[0], contracts[1], days)

    # Crack spreads
    if name.startswith("crack_"):
        crude_type = name.replace("crack_", "", 1)
        return _load_crack_series(db, crude_type, days)

    # WTI-Brent synthetic spread
    if name == "wti_brent_spread":
        wti = _load_price_series(db, "wti", days)
        brent = _load_price_series(db, "brent", days)
        if wti.empty or brent.empty:
            return pd.Series(dtype=float, name=name)
        combined = pd.DataFrame({"wti": wti, "brent": brent}).dropna()
        spread = (combined["wti"] - combined["brent"])
        spread.name = name
        return spread

    logger.warning("Unknown dataset name: %s", name)
    return pd.Series(dtype=float, name=name)


# ---------------------------------------------------------------------------
# Alignment utilities
# ---------------------------------------------------------------------------

def _align_series(series_dict: Dict[str, pd.Series]) -> pd.DataFrame:
    """
    Combine all series into a single DataFrame on a shared tz-naive date index.
    Forward-fill up to 5 days (handles weekends + weekly EIA data gaps).
    Drop any dates where ALL values are missing.

    Defensive normalization ensures:
      - All indexes are tz-naive (macro DATE column is already naive;
        all TIMESTAMPTZ columns are stripped in their individual loaders).
      - Duplicate date entries are reduced to the last value before concat.
    """
    if not series_dict:
        return pd.DataFrame()

    # Defensive pass: guarantee every series is tz-naive and deduplicated
    clean: Dict[str, pd.Series] = {}
    for name, s in series_dict.items():
        if s.empty:
            continue
        idx = s.index
        # Strip any residual timezone
        if hasattr(idx, "tz") and idx.tz is not None:
            idx = idx.tz_localize(None)
        # Ensure datetime type
        if not isinstance(idx, pd.DatetimeIndex):
            idx = pd.to_datetime(idx)
        s = pd.Series(s.values, index=idx, name=name)
        # Deduplicate date labels (takes last occurrence)
        if s.index.duplicated().any():
            s = s.groupby(level=0).last()
        clean[name] = s

    if len(clean) < 2:
        return pd.DataFrame()

    df = pd.concat(clean.values(), axis=1)
    df.columns = list(clean.keys())

    # Resample to daily, forward-fill gaps (handles weekly EIA data)
    df = df.resample("D").last()
    df = df.ffill(limit=5)
    df = df.dropna(how="all")
    return df


# ---------------------------------------------------------------------------
# Correlation computation
# ---------------------------------------------------------------------------

def _compute_pearson_matrix(
    df: pd.DataFrame, labels: List[str]
) -> Tuple[List[str], List[List[float]]]:
    """
    Compute Pearson correlation matrix for the given columns.
    Returns (valid_labels, matrix_2d).
    """
    # Keep only columns that exist and have enough data
    valid = [c for c in labels if c in df.columns and df[c].dropna().shape[0] > 5]
    if len(valid) < 2:
        return valid, []

    corr_df = df[valid].corr(method="pearson")

    # Round and convert to nested list
    matrix = []
    for row_label in valid:
        row = []
        for col_label in valid:
            val = corr_df.loc[row_label, col_label]
            row.append(round(float(val), 4) if not np.isnan(val) else None)
        matrix.append(row)

    return valid, matrix


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------

def _get_cached_matrix(
    db: Session, window: str, matrix_type: str
) -> Optional[Dict[str, Any]]:
    """Return a cached matrix if it exists and is still fresh."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=CACHE_TTL_SECONDS)
    record = (
        db.query(CorrelationSnapshot)
        .filter(
            CorrelationSnapshot.window == window,
            CorrelationSnapshot.matrix_type == matrix_type,
            CorrelationSnapshot.computed_at >= cutoff,
        )
        .order_by(CorrelationSnapshot.computed_at.desc())
        .first()
    )
    if not record:
        return None
    return {
        "window": window,
        "matrix_type": matrix_type,
        "labels": json.loads(record.labels_json),
        "matrix": json.loads(record.matrix_json),
        "computed_at": record.computed_at.isoformat(),
        "cached": True,
    }


def _cache_matrix(
    db: Session,
    window: str,
    matrix_type: str,
    labels: List[str],
    matrix: List[List[float]],
) -> None:
    """Persist a computed correlation matrix to the DB cache."""
    try:
        db.add(
            CorrelationSnapshot(
                window=window,
                matrix_type=matrix_type,
                labels_json=json.dumps(labels),
                matrix_json=json.dumps(matrix),
            )
        )
        db.commit()
    except Exception as exc:
        logger.error("Failed to cache correlation matrix: %s", exc)
        db.rollback()


# ---------------------------------------------------------------------------
# Public API: Matrix
# ---------------------------------------------------------------------------

def get_matrix(
    db: Session,
    window: str = "30D",
    matrix_type: str = "product",
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Return a heatmap-ready correlation matrix.

    Args:
        db:           Database session.
        window:       One of "7D", "30D", "90D", "180D".
        matrix_type:  One of "product", "spread", "macro", "inventory".
        force_refresh: Skip cache and recompute.

    Returns:
        {
          "window": "30D",
          "matrix_type": "product",
          "labels": [...],
          "matrix": [[...], ...],
          "computed_at": "...",
          "cached": bool
        }
    """
    if window not in VALID_WINDOWS:
        raise ValueError(f"Invalid window '{window}'. Must be one of {list(VALID_WINDOWS)}")
    if matrix_type not in MATRIX_GROUPS:
        raise ValueError(f"Invalid matrix_type '{matrix_type}'. Must be one of {list(MATRIX_GROUPS)}")

    # Try cache first
    if not force_refresh:
        cached = _get_cached_matrix(db, window, matrix_type)
        if cached:
            return cached

    days = VALID_WINDOWS[window]
    requested_names = MATRIX_GROUPS[matrix_type]

    # Load and align all series
    series_dict: Dict[str, pd.Series] = {}
    for name in requested_names:
        s = _resolve_series(db, name, days)
        if not s.empty:
            series_dict[name] = s
        else:
            logger.info("Dataset '%s' unavailable — excluded from matrix", name)

    if len(series_dict) < 2:
        return {
            "window": window,
            "matrix_type": matrix_type,
            "labels": [],
            "matrix": [],
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "cached": False,
            "error": "Insufficient data for correlation — populate datasets first",
        }

    df = _align_series(series_dict)
    labels, matrix = _compute_pearson_matrix(df, requested_names)

    result = {
        "window": window,
        "matrix_type": matrix_type,
        "labels": labels,
        "matrix": matrix,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "cached": False,
    }

    if labels and matrix:
        _cache_matrix(db, window, matrix_type, labels, matrix)

    return result


# ---------------------------------------------------------------------------
# Public API: Frontend Heatmaps
# ---------------------------------------------------------------------------

def _load_yfinance_price_series_directly(name: str, days: int) -> pd.Series:
    TICKERS = {
        'wti': 'CL=F',
        'brent': 'BZ=F',
        'gasoline': 'RB=F',
        'heating_oil': 'HO=F',
    }
    ticker = TICKERS.get(name)
    if not ticker:
        return pd.Series(dtype=float, name=name)
    return _load_yfinance_series(ticker, name, days)

def get_frontend_matrix(
    db: Session,
    window: str = "30D",
    matrix_type: str = "product",
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Return a heatmap-ready correlation matrix tailored for the frontend.
    Uses yfinance directly for sparse price datasets.
    """
    if window not in VALID_WINDOWS:
        raise ValueError(f"Invalid window '{window}'. Must be one of {list(VALID_WINDOWS)}")
    if matrix_type not in FRONTEND_GROUPS:
        raise ValueError(f"Invalid matrix_type '{matrix_type}'. Must be one of {list(FRONTEND_GROUPS)}")

    # Try cache first (prefix frontend_ to avoid colliding with generic cache)
    cache_type = f"frontend_{matrix_type}"
    if not force_refresh:
        cached = _get_cached_matrix(db, window, cache_type)
        if cached:
            cached["matrix_type"] = matrix_type  # Map back for the frontend response
            return cached

    days = VALID_WINDOWS[window]
    requested_names = FRONTEND_GROUPS[matrix_type]
    series_dict: Dict[str, pd.Series] = {}

    for name in requested_names:
        # 1. Product heatmap: fetch prices from yfinance because local prices DB is sparse
        if matrix_type == "product" and name in ["wti", "brent", "gasoline", "heating_oil"]:
            s = _load_yfinance_price_series_directly(name, days)
        # 2. Macro heatmap: fetch wti/brent from yfinance
        elif matrix_type == "macro" and name in ["wti", "brent"]:
            s = _load_yfinance_price_series_directly(name, days)
        # 3. Spread heatmap: calculate wti_brent_spread using yfinance directly
        elif name == "wti_brent_spread":
            wti = _load_yfinance_price_series_directly("wti", days)
            brent = _load_yfinance_price_series_directly("brent", days)
            if wti.empty or brent.empty:
                s = pd.Series(dtype=float, name=name)
            else:
                combined = pd.DataFrame({"wti": wti, "brent": brent}).dropna()
                s = (combined["wti"] - combined["brent"])
                s.name = name
        # 4. Spread heatmap: crack maps to crack_wti
        elif name == "crack":
            s = _resolve_series(db, "crack_wti", days)
            s.name = "crack"  # Rename so index aligns with labels
        # Default: resolve from DB
        else:
            s = _resolve_series(db, name, days)

        if not s.empty:
            series_dict[name] = s
        else:
            logger.info("Dataset '%s' unavailable — excluded from frontend matrix", name)

    if len(series_dict) < 2:
        return {
            "window": window,
            "matrix_type": matrix_type,
            "labels": [],
            "matrix": [],
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "cached": False,
            "error": "Insufficient data for correlation",
        }

    df = _align_series(series_dict)
    labels, matrix = _compute_pearson_matrix(df, requested_names)

    result = {
        "window": window,
        "matrix_type": matrix_type,
        "labels": labels,
        "matrix": matrix,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "cached": False,
    }

    if labels and matrix:
        _cache_matrix(db, window, cache_type, labels, matrix)

    return result


# ---------------------------------------------------------------------------
# Public API: Top correlations
# ---------------------------------------------------------------------------

def get_top_correlations(
    db: Session,
    window: str = "30D",
    n: int = 10,
    direction: str = "positive",
) -> List[Dict[str, Any]]:
    """
    Find the N strongest positive or negative correlations across ALL matrix types.

    Returns list of {asset_1, asset_2, correlation} sorted by |correlation|.
    """
    days = VALID_WINDOWS.get(window, 30)
    pairs: List[Tuple[str, str, float]] = []

    # Collect all unique dataset names across all matrix groups
    all_names: List[str] = []
    for names in MATRIX_GROUPS.values():
        for n_item in names:
            if n_item not in all_names:
                all_names.append(n_item)

    series_dict: Dict[str, pd.Series] = {}
    for name in all_names:
        s = _resolve_series(db, name, days)
        if not s.empty:
            series_dict[name] = s

    if len(series_dict) < 2:
        return []

    df = _align_series(series_dict)
    valid_cols = [c for c in series_dict if c in df.columns and df[c].dropna().shape[0] > 5]

    if len(valid_cols) < 2:
        return []

    corr_df = df[valid_cols].corr(method="pearson")

    # Extract all unique pairs
    for i, a1 in enumerate(valid_cols):
        for a2 in valid_cols[i + 1:]:
            val = corr_df.loc[a1, a2]
            if not np.isnan(val):
                pairs.append((a1, a2, round(float(val), 4)))

    if direction == "positive":
        pairs.sort(key=lambda x: x[2], reverse=True)
        selected = [p for p in pairs if p[2] > 0]
    else:
        pairs.sort(key=lambda x: x[2])
        selected = [p for p in pairs if p[2] < 0]

    return [
        {"asset_1": p[0], "asset_2": p[1], "correlation": p[2]}
        for p in selected[:n]
    ]
