"""
opec_production_service.py
--------------------------
Service layer for OPEC total crude oil production data.

Data Source
-----------
EIA Short-Term Energy Outlook (STEO) API v2
  Series  : PAPR_OPEC  — "Total OPEC Petroleum Supply" (million barrels/day)
  URL base: https://api.eia.gov/v2/steo/data/
  Frequency: monthly
  Coverage : 1993-01 → present + short-term forecasts

Functions
---------
fetch_opec_production()          – Pull all available monthly rows from EIA.
store_opec_production(db, rows)  – Upsert rows into opec_production, skip dupes.
get_opec_production_history(db)  – Read stored history from PostgreSQL.
"""

import os
import logging
from typing import List, Dict, Any, Optional

import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.opec_production import OpecProduction

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

load_dotenv()

logger = logging.getLogger(__name__)

EIA_API_KEY = os.getenv("EIA_API_KEY", "")
EIA_STEO_URL = "https://api.eia.gov/v2/steo/data/"
SERIES_ID = "PAPR_OPEC"
SOURCE_LABEL = "EIA STEO API — PAPR_OPEC (Total OPEC Petroleum Supply, mb/d)"
PAGE_SIZE = 5000  # EIA max is effectively unlimited with length param; 5000 covers all history


# ---------------------------------------------------------------------------
# fetch_opec_production
# ---------------------------------------------------------------------------

def fetch_opec_production() -> List[Dict[str, Any]]:
    """
    Download all available monthly OPEC total petroleum supply rows from the
    EIA STEO API (series PAPR_OPEC).

    Returns
    -------
    List of dicts, each with keys:
        report_month   : str  YYYY-MM
        production_mbd : float  million barrels per day
        source_report  : str  human-readable source label

    Raises
    ------
    RuntimeError if EIA_API_KEY is not configured.
    requests.HTTPError on non-200 responses.
    """
    if not EIA_API_KEY:
        logger.error("EIA_API_KEY is not set — cannot fetch OPEC production data.")
        raise RuntimeError("EIA_API_KEY environment variable is not configured.")

    params = {
        "api_key": EIA_API_KEY,
        "frequency": "monthly",
        "data[0]": "value",
        "facets[seriesId][]": SERIES_ID,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": PAGE_SIZE,
    }

    logger.info("Fetching OPEC production from EIA STEO API | URL: %s | series: %s",
                EIA_STEO_URL, SERIES_ID)

    response = requests.get(EIA_STEO_URL, params=params, timeout=30)
    response.raise_for_status()

    raw_rows = response.json().get("response", {}).get("data", [])
    logger.info("EIA API returned %d raw rows for series %s", len(raw_rows), SERIES_ID)

    parsed: List[Dict[str, Any]] = []
    skipped = 0

    for row in raw_rows:
        period = row.get("period", "")
        raw_val = row.get("value")

        # ── Validation ─────────────────────────────────────────────────────
        # 1. Period must be YYYY-MM
        if not period or len(period) != 7 or period[4] != "-":
            logger.warning("Skipping row with invalid period format: %r", period)
            skipped += 1
            continue

        # 2. Value must be convertible to a positive float
        if raw_val is None:
            logger.warning("Skipping row for period %s: value is None", period)
            skipped += 1
            continue
        try:
            val = float(raw_val)
        except (ValueError, TypeError):
            logger.warning("Skipping row for period %s: cannot parse value %r as float", period, raw_val)
            skipped += 1
            continue
        if val <= 0:
            logger.warning("Skipping row for period %s: non-positive value %.4f", period, val)
            skipped += 1
            continue

        parsed.append({
            "report_month": period,
            "production_mbd": round(val, 6),
            "source_report": SOURCE_LABEL,
        })

    logger.info(
        "fetch_opec_production complete | parsed=%d valid rows | skipped=%d invalid rows",
        len(parsed), skipped,
    )
    return parsed


# ---------------------------------------------------------------------------
# store_opec_production
# ---------------------------------------------------------------------------

def store_opec_production(db: Session, rows: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Upsert a list of parsed OPEC production rows into the opec_production table.

    Strategy: try to INSERT each row; on UniqueConstraint violation (duplicate
    report_month) skip the row and continue.  This guarantees idempotent
    re-ingestion without data loss.

    Parameters
    ----------
    db   : SQLAlchemy session
    rows : output of fetch_opec_production()

    Returns
    -------
    dict with keys: inserted, skipped_duplicates, errors
    """
    inserted = 0
    skipped_duplicates = 0
    errors = 0

    logger.info("store_opec_production: attempting to insert %d rows", len(rows))

    for row in rows:
        try:
            record = OpecProduction(
                report_month=row["report_month"],
                production_mbd=row["production_mbd"],
                source_report=row["source_report"],
            )
            db.add(record)
            db.flush()  # flush individually so IntegrityError is caught per-row
            inserted += 1
        except IntegrityError:
            db.rollback()
            skipped_duplicates += 1
            logger.debug("Duplicate skipped for report_month=%s", row.get("report_month"))
        except Exception as exc:
            db.rollback()
            errors += 1
            logger.error("Error inserting row %s: %s", row.get("report_month"), exc)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error("Final commit failed: %s", exc)

    logger.info(
        "store_opec_production complete | inserted=%d | skipped_duplicates=%d | errors=%d",
        inserted, skipped_duplicates, errors,
    )
    return {"inserted": inserted, "skipped_duplicates": skipped_duplicates, "errors": errors}


# ---------------------------------------------------------------------------
# get_opec_production_history
# ---------------------------------------------------------------------------

def get_opec_production_history(
    db: Session,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Read OPEC production history from PostgreSQL, ordered ascending by month.

    Parameters
    ----------
    db    : SQLAlchemy session
    limit : if provided, return only the most recent N months

    Returns
    -------
    List of dicts: [{month: str, production: float}, ...]
    """
    query = db.query(OpecProduction).order_by(OpecProduction.report_month.asc())
    if limit:
        # Grab the tail (most recent N) after sorting
        all_rows = query.all()
        rows = all_rows[-limit:] if len(all_rows) > limit else all_rows
    else:
        rows = query.all()

    logger.info("get_opec_production_history: returning %d rows from DB", len(rows))
    return [
        {"month": r.report_month, "production": r.production_mbd}
        for r in rows
    ]
