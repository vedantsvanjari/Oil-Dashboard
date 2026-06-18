import os
import asyncio
import logging
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.api import prices, news, inventories, refineries, macro, spreads, crack, correlations, opec, sentiment, signals
from app.api import opec_production as opec_production_api
from app.api import regimes, statistical_signals, replay
import app.models  # Ensures all SQLAlchemy models are imported
from app.models.base import Base
from app.models.inventories import Inventory
from app.models.refineries import RefineryData
from app.models.macro import MacroData
from app.database.connection import engine, get_db, SessionLocal
from app.services.price_service import fetch_intraday_prices

logger = logging.getLogger(__name__)

# Create tables if they do not exist
Base.metadata.create_all(bind=engine)

# DEBUG gate: debug/admin endpoints are only registered when explicitly enabled.
# Set DEBUG=true in the environment for local development; leave unset in production.
DEBUG = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")

# Background 15-minute intraday price ingestion. Disable with ENABLE_INGESTION=false
# (e.g. in tests/CI where outbound network is unavailable).
ENABLE_INGESTION = os.getenv("ENABLE_INGESTION", "true").lower() in ("1", "true", "yes")
INGESTION_INTERVAL_SECONDS = 15 * 60


async def _intraday_ingestion_loop():
    """Fetch and persist 15-minute bars on a fixed cadence until cancelled."""
    while True:
        db = SessionLocal()
        try:
            # yfinance + DB writes are blocking; run off the event loop.
            await asyncio.to_thread(fetch_intraday_prices, db)
        except asyncio.CancelledError:
            db.close()
            raise
        except Exception as e:  # never let the loop die on a transient error
            logger.error("Intraday ingestion loop error: %s", e)
        finally:
            db.close()
        await asyncio.sleep(INGESTION_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = None
    if ENABLE_INGESTION:
        logger.info("Starting intraday ingestion task (every %ss)", INGESTION_INTERVAL_SECONDS)
        task = asyncio.create_task(_intraday_ingestion_loop())
    yield
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(lifespan=lifespan)

# CORS: allow the frontend origin(s). Configure via CORS_ORIGINS (comma-separated);
# defaults to the local Vite dev server.
_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prices.router, prefix="/api/prices", tags=["prices"])
app.include_router(news.router, prefix="/api/news", tags=["news"])
app.include_router(inventories.router, prefix="/api/inventories", tags=["inventories"])
app.include_router(refineries.router, prefix="/api/refineries", tags=["refineries"])
app.include_router(macro.router, prefix="/api/macro", tags=["macro"])
app.include_router(spreads.router, prefix="/api/spreads", tags=["spreads"])
app.include_router(crack.router, prefix="/api/crack", tags=["crack"])
app.include_router(correlations.router, prefix="/api/correlations", tags=["correlations"])
app.include_router(opec.router, prefix="/api/opec", tags=["opec"])
app.include_router(opec_production_api.router, prefix="/api/opec", tags=["opec-production"])
app.include_router(sentiment.router, prefix="/api/sentiment", tags=["sentiment"])
app.include_router(signals.router, prefix="/api/signals", tags=["signals"])
app.include_router(regimes.router, prefix="/api/regimes", tags=["regimes"])
app.include_router(statistical_signals.router, prefix="/api/signals/statistical", tags=["statistical-signals"])
app.include_router(replay.router, prefix="/api/replay", tags=["replay"])

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Debug and admin endpoints are only mounted when DEBUG is enabled. They leak
# secrets (key prefixes) and perform unauthenticated row deletes, so they must
# never be exposed in production.
if DEBUG:
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
