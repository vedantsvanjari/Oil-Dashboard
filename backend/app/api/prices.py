from fastapi import APIRouter
from app.services.price_service import fetch_live_prices

router = APIRouter()

@router.get("/live")
def get_live_prices():
    return fetch_live_prices()
