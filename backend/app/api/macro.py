from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database.connection import get_db
from app.services.macro_service import fetch_and_store_macro_data, get_latest_macro_data, get_historical_macro_data

router = APIRouter()

@router.get("/latest")
def get_macro_latest(db: Session = Depends(get_db)):
    # Trigger a sync with Yahoo Finance
    fetch_and_store_macro_data(db, period="5d")
    
    data = get_latest_macro_data(db)
    if data:
        return data
    return {"message": "No macro data available"}

@router.get("/history")
def get_macro_history(db: Session = Depends(get_db)):
    # Optionally trigger a larger sync or just rely on scheduled jobs.
    # We will trigger a full 1-year sync if the DB is empty or just regularly fetch.
    # To avoid rate limits on every /history call, we'll just return what's in DB.
    # If the DB is completely empty, trigger a larger fetch.
    data = get_historical_macro_data(db, limit=260)
    if not data:
        fetch_and_store_macro_data(db, period="1y")
        data = get_historical_macro_data(db, limit=260)
    return data
