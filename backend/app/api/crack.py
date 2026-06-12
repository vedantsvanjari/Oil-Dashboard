"""
Crack Spread API Router
========================
Exposes 3:2:1 refinery margin analytics for WTI and Brent.

Routes:
  GET  /api/crack/latest      ?crude_type=wti
  GET  /api/crack/history     ?crude_type=wti&days=365
  GET  /api/crack/statistics  ?crude_type=wti
  POST /api/crack/refresh     Trigger recompute for all crude types
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.crack_spread_service import (
    compute_and_store_crack_spreads,
    latest_crack,
    crack_history,
    crack_statistics,
)

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_CRUDE_TYPES = {"wti", "brent"}


@router.get("/latest", summary="Latest 3:2:1 crack spread")
def get_latest_crack(
    crude_type: str = Query("wti", description="'wti' or 'brent'"),
    db: Session = Depends(get_db),
):
    """
    Return the most recent 3:2:1 crack spread for the given crude type.
    Triggers a compute-and-store if no data exists yet.

    The crack spread = (2 × RBOB + 1 × Heating Oil − 3 × Crude) / 3 ($/bbl)
    """
    crude_type = crude_type.lower()
    if crude_type not in VALID_CRUDE_TYPES:
        raise HTTPException(status_code=400, detail=f"crude_type must be one of {VALID_CRUDE_TYPES}")

    result = latest_crack(db, crude_type)

    if result is None:
        logger.info("No crack spread data for %s — triggering compute", crude_type)
        compute_and_store_crack_spreads(db)
        result = latest_crack(db, crude_type)

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Data unavailable — yfinance price fetch failed. Try again shortly.",
        )

    return result


@router.get("/history", summary="3:2:1 crack spread history")
def get_crack_history(
    crude_type: str = Query("wti"),
    days: int = Query(365, ge=1, le=1825, description="Look-back in calendar days"),
    db: Session = Depends(get_db),
):
    """
    Return the historical time series of the 3:2:1 crack spread.
    Results sorted ascending by timestamp.
    """
    crude_type = crude_type.lower()
    if crude_type not in VALID_CRUDE_TYPES:
        raise HTTPException(status_code=400, detail=f"crude_type must be one of {VALID_CRUDE_TYPES}")

    data = crack_history(db, crude_type, days=days)

    if not data:
        compute_and_store_crack_spreads(db)
        data = crack_history(db, crude_type, days=days)

    return {
        "crude_type": crude_type,
        "days_requested": days,
        "count": len(data),
        "history": data,
    }


@router.get("/statistics", summary="3:2:1 crack spread statistics")
def get_crack_statistics(
    crude_type: str = Query("wti"),
    db: Session = Depends(get_db),
):
    """
    Return summary statistics for the given crude type's crack spread:
    latest, 30-day average, 90-day average, volatility, trend direction.
    """
    crude_type = crude_type.lower()
    if crude_type not in VALID_CRUDE_TYPES:
        raise HTTPException(status_code=400, detail=f"crude_type must be one of {VALID_CRUDE_TYPES}")

    stats = crack_statistics(db, crude_type)

    if stats["sample_size"] == 0:
        compute_and_store_crack_spreads(db)
        stats = crack_statistics(db, crude_type)

    return stats


@router.post("/refresh", summary="Recompute all crack spreads")
def refresh_crack_spreads(db: Session = Depends(get_db)):
    """
    Trigger a full recompute of 3:2:1 crack spreads for all crude types.
    Returns a summary of rows upserted per crude type.
    """
    summary = compute_and_store_crack_spreads(db)
    return {"status": "ok", "upserted": summary}
