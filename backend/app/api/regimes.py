from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
import os
import json
import pandas as pd
from typing import Dict, Any

from app.database.connection import get_db
from app.services.statistical_signal_engine import StatisticalSignalEngine

router = APIRouter()

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
    df = pd.read_sql_query(query, db.bind)
    
    if df.empty:
        raise HTTPException(status_code=404, detail="No data available in regime_targets")
        
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
