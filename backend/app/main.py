from fastapi import FastAPI
from app.api import prices, news
import app.models  # Ensures all SQLAlchemy models are imported
from app.models.base import Base
from app.database.connection import engine

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(prices.router, prefix="/api/prices", tags=["prices"])
app.include_router(news.router, prefix="/api/news", tags=["news"])

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/debug/tables")
def get_debug_tables():
    return list(Base.metadata.tables.keys())
