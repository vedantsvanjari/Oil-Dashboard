"""
Spreads API Router
==================
Exposes both the legacy Brent-WTI spread and the new calendar spread analytics.

Existing routes (preserved):
  GET /api/spreads/brent-wti

New routes (calendar spreads):
  GET /api/spreads/latest       ?commodity=wti&contract1=M1&contract2=M2
  GET /api/spreads/history      ?commodity=wti&contract1=M1&contract2=M2&days=365
  GET /api/spreads/statistics   ?commodity=wti&contract1=M1&contract2=M2
  POST /api/spreads/refresh     Trigger recompute for all pairs
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.spread_service import get_brent_wti_spread
from app.services.calendar_spread_service import (
    compute_and_store_calendar_spreads,
    latest_spread,
    spread_history,
    spread_statistics,
)

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_COMMODITIES = {"wti", "brent"}
VALID_CONTRACTS = {"M1", "M2", "M3", "M4", "M6", "M12"}


# ---------------------------------------------------------------------------
# Legacy route — preserved as-is
# ---------------------------------------------------------------------------

@router.get("/brent-wti", summary="Brent-WTI quality spread (legacy)")
def get_spread(db: Session = Depends(get_db)):
    """Brent minus WTI price spread computed from stored price history."""
    return get_brent_wti_spread(db)


# ---------------------------------------------------------------------------
# Calendar spread routes
# ---------------------------------------------------------------------------

@router.get("/latest", summary="Latest calendar spread value")
def get_latest_spread(
    commodity: str = Query("wti", description="'wti' or 'brent'"),
    contract1: str = Query("M1", description="Near contract: M1, M2, M3"),
    contract2: str = Query("M2", description="Far contract: M2, M3, M4, M6, M12"),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """
    Return the most recent calendar spread value for the given commodity/contract pair.
    Triggers a background data refresh if no data is found.
    """
    commodity = commodity.lower()
    contract1 = contract1.upper()
    contract2 = contract2.upper()

    if commodity not in VALID_COMMODITIES:
        raise HTTPException(status_code=400, detail=f"commodity must be one of {VALID_COMMODITIES}")
    if contract1 not in VALID_CONTRACTS or contract2 not in VALID_CONTRACTS:
        raise HTTPException(status_code=400, detail=f"contracts must be one of {VALID_CONTRACTS}")

    result = latest_spread(db, commodity, contract1, contract2)

    if result is None:
        # Trigger synchronous fetch on first call
        logger.info("No data for %s %s-%s — triggering compute", commodity, contract1, contract2)
        compute_and_store_calendar_spreads(db)
        result = latest_spread(db, commodity, contract1, contract2)

    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Data unavailable — price history could not be fetched. Try again shortly.",
        )

    return result


@router.get("/history", summary="Calendar spread history")
def get_spread_history(
    commodity: str = Query("wti"),
    contract1: str = Query("M1"),
    contract2: str = Query("M2"),
    days: int = Query(365, ge=1, le=1825, description="Number of calendar days to look back"),
    db: Session = Depends(get_db),
):
    """
    Return historical calendar spread time series for the given pair.
    Results are sorted ascending by timestamp.
    """
    commodity = commodity.lower()
    contract1 = contract1.upper()
    contract2 = contract2.upper()

    if commodity not in VALID_COMMODITIES:
        raise HTTPException(status_code=400, detail=f"commodity must be one of {VALID_COMMODITIES}")

    data = spread_history(db, commodity, contract1, contract2, days=days)

    if not data:
        # Attempt refresh
        compute_and_store_calendar_spreads(db)
        data = spread_history(db, commodity, contract1, contract2, days=days)

    return {
        "commodity": commodity,
        "contract1": contract1,
        "contract2": contract2,
        "days_requested": days,
        "count": len(data),
        "history": data,
    }


@router.get("/statistics", summary="Calendar spread statistics")
def get_spread_statistics(
    commodity: str = Query("wti"),
    contract1: str = Query("M1"),
    contract2: str = Query("M2"),
    db: Session = Depends(get_db),
):
    """
    Return summary statistics for the given calendar spread pair:
    latest value, daily/weekly/monthly change, annualised volatility, z-score.
    """
    commodity = commodity.lower()
    contract1 = contract1.upper()
    contract2 = contract2.upper()

    if commodity not in VALID_COMMODITIES:
        raise HTTPException(status_code=400, detail=f"commodity must be one of {VALID_COMMODITIES}")

    stats = spread_statistics(db, commodity, contract1, contract2)

    if stats["sample_size"] == 0:
        compute_and_store_calendar_spreads(db)
        stats = spread_statistics(db, commodity, contract1, contract2)

    return stats


@router.post("/refresh", summary="Recompute all calendar spreads")
def refresh_spreads(db: Session = Depends(get_db)):
    """
    Trigger a full recompute of all calendar spread pairs for WTI and Brent.
    Returns a summary of rows upserted per pair.
    """
    summary = compute_and_store_calendar_spreads(db)
    return {"status": "ok", "upserted": summary}
