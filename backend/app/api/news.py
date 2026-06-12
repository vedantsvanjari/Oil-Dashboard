from fastapi import APIRouter
from app.services.news_service import news_service

router = APIRouter()

@router.get("")
def get_news():
    data = news_service.fetch_news()
    return data["articles"]

@router.get("/sentiment")
def get_news_sentiment():
    data = news_service.fetch_news()
    return data["sentiment_summary"]
