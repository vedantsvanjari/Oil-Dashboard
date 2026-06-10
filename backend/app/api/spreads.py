from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.spread_service import get_brent_wti_spread

router = APIRouter()

@router.get("/brent-wti")
def get_spread(db: Session = Depends(get_db)):
    return get_brent_wti_spread(db)
