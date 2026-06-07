from fastapi import FastAPI
from app.api import prices

app = FastAPI()

app.include_router(prices.router, prefix="/api/prices", tags=["prices"])

@app.get("/health")
def health_check():
    return {"status": "ok"}
