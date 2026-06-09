from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.inventory_service import fetch_eia_inventories, fetch_historical_inventories

router = APIRouter()

@router.get("")
def get_inventories(db: Session = Depends(get_db)):
    return fetch_eia_inventories(db)

@router.get("/history")
def get_historical_inventories():
    return fetch_historical_inventories()
