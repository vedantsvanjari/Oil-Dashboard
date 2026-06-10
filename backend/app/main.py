import os
import requests
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.api import prices, news, inventories, refineries, macro, spreads
import app.models  # Ensures all SQLAlchemy models are imported
from app.models.base import Base
from app.models.inventories import Inventory
from app.models.refineries import RefineryData
from app.models.macro import MacroData
from app.database.connection import engine, get_db

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(prices.router, prefix="/api/prices", tags=["prices"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(inventories.router, prefix="/api/inventories", tags=["inventories"])
app.include_router(refineries.router, prefix="/api/refineries", tags=["refineries"])
app.include_router(macro.router, prefix="/api/macro", tags=["macro"])
app.include_router(spreads.router, prefix="/api/spreads", tags=["spreads"])

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/api/debug/tables")
def get_debug_tables():
    return list(Base.metadata.tables.keys())

@app.get("/api/debug/twelve-data")
def debug_twelve_data():
    from app.services.twelvedata_service import get_twelve_data_client
    client_config = get_twelve_data_client()
    key = client_config.get("api_key", "")
    return {
        "api_key_loaded": bool(key),
        "api_key_length": len(key),
        "first_5_chars": key[:5] if key else ""
    }

@app.get("/api/debug/eia-test")
def debug_eia_test():
    EIA_API_KEY = os.getenv("EIA_API_KEY", "")
    series_id = "PET.WCRSTUS1.W"
    url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value&facets[series][]={series_id}&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1"
    
    try:
        response = requests.get(url)
        try:
            json_data = response.json()
        except Exception:
            json_data = {"error": "Failed to parse JSON", "text": response.text}
            
        return {
            "url": url,
            "status_code": response.status_code,
            "response": json_data
        }
    except Exception as e:
        return {
            "url": url,
            "status_code": 500,
            "error": str(e)
        }

@app.get("/api/debug/eia-metadata")
def debug_eia_metadata():
    EIA_API_KEY = os.getenv("EIA_API_KEY", "")
    url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/?api_key={EIA_API_KEY}"
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/debug/inventory-db")
def debug_inventory_db(db: Session = Depends(get_db)):
    return db.query(Inventory).order_by(Inventory.date.desc()).limit(20).all()

@app.post("/api/admin/cleanup-inventory")
def cleanup_inventory(db: Session = Depends(get_db)):
    deleted_count = db.query(Inventory).filter(Inventory.quantity == 0).delete()
    db.commit()
    return {"deleted_rows": deleted_count}

@app.post("/api/admin/cleanup-macro")
def cleanup_macro(db: Session = Depends(get_db)):
    deleted_count = db.query(MacroData).filter(
        (MacroData.dxy == None) | (MacroData.us10y == None)
    ).delete()
    db.commit()
    return {"deleted_rows": deleted_count}
