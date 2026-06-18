from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import pandas as pd
from typing import Dict, Any, List

from app.database.connection import get_db
from app.services.statistical_signal_engine import StatisticalSignalEngine

router = APIRouter()

def _is_missing_table(exc: Exception) -> bool:
    """True when the exception indicates regime_targets does not exist."""
    text = str(getattr(exc, "orig", exc)).lower()
    return "regime_targets" in text or "no such table" in text or "does not exist" in text


@router.get("", summary="Get real-time statistical signals")
def get_statistical_signals(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    # Query the latest row from regime_targets. The table is created by the offline
    # pipeline (clean_and_target.py); if it has not run yet, return an empty signal
    # list instead of crashing with a 500.
    query = "SELECT * FROM regime_targets ORDER BY timestamp DESC LIMIT 1"
    try:
        df = pd.read_sql_query(query, db.bind)
    except Exception as exc:
        if _is_missing_table(exc):
            return []
        raise

    if df.empty:
        return []
        
    row = df.iloc[0]
    
    try:
        engine = StatisticalSignalEngine()
        signals = engine.generate_signals(row)
        
        # Attach timestamp to signals for clarity
        timestamp = str(row['timestamp'])
        for sig in signals:
            sig['Timestamp'] = timestamp
            
        return signals
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Statistical memory map not found. Please run precomputation.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
