from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.services.price_service import fetch_live_prices, fetch_historical_prices, get_intraday_prices
from app.database.connection import get_db
from app.models.prices import Price

router = APIRouter()

@router.get("/live")
def get_live_prices(db: Session = Depends(get_db)):
    return fetch_live_prices(db)

@router.get("/db")
def get_db_prices(db: Session = Depends(get_db)):
    prices = db.query(Price).order_by(Price.timestamp.desc()).limit(20).all()
    return prices

@router.get("/history/{symbol}")
def get_historical_prices(symbol: str):
    data = fetch_historical_prices(symbol.lower())
    if data is None:
        raise HTTPException(status_code=404, detail="Unsupported symbol")
    return data

@router.get("/intraday/{symbol}")
def get_intraday(
    symbol: str,
    days: int = Query(5, ge=1, le=60),
    db: Session = Depends(get_db),
):
    """Persisted 15-minute intraday series for a symbol (populated by the background ingestion task)."""
    data = get_intraday_prices(db, symbol.lower(), days=days)
    if data is None:
        raise HTTPException(status_code=404, detail="Unsupported symbol")
    return data
