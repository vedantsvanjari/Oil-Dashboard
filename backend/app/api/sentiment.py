from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.sentiment_engine import compute_sentiment

router = APIRouter()

@router.get("")
def get_sentiment(db: Session = Depends(get_db)):
    """
    Computes real-time market sentiment based on backend fundamental models.
    """
    return compute_sentiment(db)
