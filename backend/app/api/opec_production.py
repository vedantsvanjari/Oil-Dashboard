"""
opec_production.py  (API router)
---------------------------------
Exposes OPEC total crude oil production data stored in PostgreSQL.

Routes
------
GET  /api/opec/production          — Return latest value + full history
POST /api/opec/production/refresh  — Trigger re-ingestion from EIA API
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.opec_production_service import (
    fetch_opec_production,
    store_opec_production,
    get_opec_production_history,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helper — seed DB if empty
# ---------------------------------------------------------------------------

def _ensure_data(db: Session) -> None:
    """Trigger a fresh ingestion if the table is empty."""
    from app.models.opec_production import OpecProduction
    count = db.query(OpecProduction).count()
    if count == 0:
        logger.info("opec_production table is empty — triggering initial ingestion")
        rows = fetch_opec_production()
        result = store_opec_production(db, rows)
        logger.info("Initial ingestion complete: %s", result)


# ---------------------------------------------------------------------------
# GET /api/opec/production
# ---------------------------------------------------------------------------

@router.get(
    "/production",
    summary="OPEC Total Petroleum Supply — history",
    response_description=(
        "Latest production value (mb/d) and full monthly history from 1993 to present."
    ),
)
def get_opec_production(db: Session = Depends(get_db)):
    """
    Return OPEC total petroleum supply data.

    On first call the table is populated automatically from the EIA STEO API
    (series PAPR_OPEC) if it is empty.

    Response
    --------
    {
      "latest_production": <float, mb/d>,
      "history": [
        {"month": "YYYY-MM", "production": <float>},
        ...
      ]
    }
    """
    try:
        _ensure_data(db)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("Error during auto-ingestion: %s", exc)
        raise HTTPException(status_code=500, detail="Data ingestion failed. Try /refresh.")

    history = get_opec_production_history(db)

    if not history:
        raise HTTPException(
            status_code=503,
            detail="No OPEC production data available. Use POST /api/opec/production/refresh.",
        )

    latest_production = history[-1]["production"] if history else None

    logger.info(
        "GET /api/opec/production — returning %d history points, latest=%.3f mb/d",
        len(history),
        latest_production or 0,
    )

    return {
        "latest_production": latest_production,
        "history": history,
    }


# ---------------------------------------------------------------------------
# POST /api/opec/production/refresh
# ---------------------------------------------------------------------------

@router.post(
    "/production/refresh",
    summary="Re-ingest OPEC production data from EIA",
)
def refresh_opec_production(db: Session = Depends(get_db)):
    """
    Pull the latest OPEC petroleum supply data from the EIA STEO API and
    upsert into opec_production.  Existing months are skipped (no overwrites).

    Returns a summary of the ingestion run.
    """
    try:
        rows = fetch_opec_production()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        logger.error("fetch_opec_production failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"EIA fetch failed: {exc}")

    result = store_opec_production(db, rows)

    total_stored = db.query(__import__(
        "app.models.opec_production", fromlist=["OpecProduction"]
    ).OpecProduction).count()

    return {
        "status": "ok",
        "fetched_from_api": len(rows),
        "inserted": result["inserted"],
        "skipped_duplicates": result["skipped_duplicates"],
        "errors": result["errors"],
        "total_rows_in_db": total_stored,
    }
