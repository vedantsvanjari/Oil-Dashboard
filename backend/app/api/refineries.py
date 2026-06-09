from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.refinery_service import fetch_latest_refinery_data, fetch_historical_refinery_data

router = APIRouter()

@router.get("/latest")
def get_latest_refinery_data(db: Session = Depends(get_db)):
    return fetch_latest_refinery_data(db)

@router.get("/history")
def get_historical_refinery_data():
    return fetch_historical_refinery_data()
