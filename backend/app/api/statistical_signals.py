from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import pandas as pd
from typing import Dict, Any, List

from app.database.connection import get_db
from app.services.statistical_signal_engine import StatisticalSignalEngine

router = APIRouter()

@router.get("", summary="Get real-time statistical signals")
def get_statistical_signals(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    # Query the latest row from regime_targets
    query = "SELECT * FROM regime_targets ORDER BY timestamp DESC LIMIT 1"
    df = pd.read_sql_query(query, db.bind)
    
    if df.empty:
        raise HTTPException(status_code=404, detail="No data available in regime_targets")
        
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
