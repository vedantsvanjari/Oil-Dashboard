from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import os
import json
import logging
import pandas as pd
from typing import Dict, Any, List

from app.database.connection import get_db
from app.services.statistical_signal_engine import StatisticalSignalEngine

logger = logging.getLogger(__name__)
router = APIRouter()

# The regime label directly encodes how pronounced the structure is, so we map it to a
# confidence flag deterministically (no guessing): "Deep" regimes are High-confidence
# structural states, the plain backwardation/contango regimes Medium, Neutral is Low.
CONFIDENCE_BY_REGIME = {
    "Deep Backwardation": "High",
    "Deep Contango": "High",
    "Backwardation": "Medium",
    "Contango": "Medium",
    "Neutral": "Low",
}

# regime_targets is created dynamically by the offline pipeline (clean_and_target.py),
# not by Alembic. Until that pipeline runs the table does not exist. A missing table
# surfaces as ProgrammingError (Postgres) or OperationalError (SQLite); we treat both
# as "pipeline not run yet" rather than letting them bubble up as a 500.
PIPELINE_NOT_RUN_MSG = "Data pipeline has not been run yet"


def _is_missing_table(exc: Exception) -> bool:
    """True when the exception indicates regime_targets does not exist."""
    text = str(getattr(exc, "orig", exc)).lower()
    return "regime_targets" in text or "no such table" in text or "does not exist" in text

def get_memory_map():
    path = os.path.join(os.path.dirname(__file__), "../models/ml/statistical_memory_map.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=503, detail="Statistical memory map not generated yet.")
    with open(path, 'r') as f:
        return json.load(f)

@router.get("/current", summary="Get current structural regime state")
def get_current_regime(db: Session = Depends(get_db)) -> Dict[str, Any]:
    # Query the latest row
    query = "SELECT timestamp, m1_m12 FROM regime_targets ORDER BY timestamp DESC LIMIT 1"
    try:
        df = pd.read_sql_query(query, db.bind)
    except Exception as exc:
        # pandas may wrap the DB error (ProgrammingError/OperationalError) in its own
        # DatabaseError, so discriminate on the message rather than the exception type.
        if _is_missing_table(exc):
            return {"available": False, "message": PIPELINE_NOT_RUN_MSG}
        raise

    if df.empty:
        return {"available": False, "message": PIPELINE_NOT_RUN_MSG}
        
    m1_m12 = float(df.iloc[0]['m1_m12'])
    timestamp = str(df.iloc[0]['timestamp'])
    
    memory_map = get_memory_map()
    thresholds = memory_map.get("regime_thresholds", {})
    
    # Initialize engine to reuse detection logic
    engine = StatisticalSignalEngine()
    current_regime = engine.detect_regime(m1_m12)
    
    regime_score = memory_map.get("regimes", {}).get(current_regime, {}).get("metrics", {}).get("regime_quality_score", 0.0)
    
    return {
        "timestamp": timestamp,
        "current_regime": current_regime,
        "regime_score": round(regime_score, 2),
        "m1_m12_value": round(m1_m12, 4),
        "thresholds": thresholds,
        "confidence": "High" if regime_score > 60 else ("Medium" if regime_score > 30 else "Low")
    }

@router.get("/statistics", summary="Get behavioral statistics per regime")
def get_regime_statistics() -> Dict[str, Any]:
    memory_map = get_memory_map()
    return memory_map.get("regimes", {})


def query_regime_history(db: Session, limit: int, days: int) -> List[Dict[str, Any]]:
    """Extract the historical regime/signal series from the pipeline-generated
    regime_targets table.

    Pulls the most recent `limit` rows, then narrows to the `days` window relative to
    the latest record (so an old historical dataset still returns data). Returns a list
    of audit-friendly records (date, regime, regime_score, m1_m12, confidence). Returns
    an empty list — never a 503 — if the pipeline hasn't generated the table yet.
    """
    query = (
        "SELECT timestamp, regime, regime_strength, m1_m12 "
        "FROM regime_targets ORDER BY timestamp DESC LIMIT :limit"
    )
    try:
        df = pd.read_sql_query(query, db.bind, params={"limit": int(limit)})
    except Exception as exc:
        # pandas may wrap the DB error in its own DatabaseError; match on the message.
        if _is_missing_table(exc):
            logger.info("Regime history requested but %s", PIPELINE_NOT_RUN_MSG.lower())
            return []
        raise

    if df.empty:
        return []

    # Narrow to the look-back window relative to the newest available record.
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    cutoff = df["timestamp"].max() - pd.Timedelta(days=days)
    df = df[df["timestamp"] >= cutoff]

    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        regime = row.get("regime")
        score = row.get("regime_strength")
        m1_m12 = row.get("m1_m12")
        records.append({
            "date": row["timestamp"].isoformat(),
            "regime": regime,
            # In this schema the per-row regime score is regime_strength (|m1_m12|).
            "regime_score": round(float(score), 4) if pd.notna(score) else None,
            "m1_m12": round(float(m1_m12), 4) if pd.notna(m1_m12) else None,
            "confidence": CONFIDENCE_BY_REGIME.get(regime, "Unknown"),
        })
    return records


@router.get("/history", summary="Historical regime/signal analytics series")
def get_regime_history(
    limit: int = Query(100, ge=1, le=100000, description="Max number of most-recent rows to return"),
    days: int = Query(90, ge=1, le=3650, description="Look-back window in days, relative to the latest record"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Full historical series of regime analytics for auditing ML/pipeline output.

    Safe on a clean database: if the pipeline has not generated regime_targets yet,
    returns `[]` with a 200 status instead of raising.
    """
    return query_regime_history(db, limit=limit, days=days)
