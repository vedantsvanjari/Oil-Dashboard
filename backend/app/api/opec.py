from fastapi import APIRouter, HTTPException
from app.services.opec_service import opec_service
from cachetools import cached, TTLCache

router = APIRouter()

# Cache for 1 hour to prevent hitting EIA API too frequently
cache = TTLCache(maxsize=10, ttl=3600)

@router.get("/latest")
@cached(cache)
def get_latest_opec():
    data = opec_service.get_opec_data()
    if "error" in data:
        raise HTTPException(status_code=500, detail=data["error"])
    return data
