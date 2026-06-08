from fastapi import APIRouter
from app.services.news_service import fetch_latest_news

router = APIRouter()

@router.get("")
def get_news():
    return fetch_latest_news()
