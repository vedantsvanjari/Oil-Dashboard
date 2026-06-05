"""
Oil Trading Desk — FastAPI Main Server

Entrypoint for the backend. Manages:
  - FastAPI app with CORS
  - WebSocket endpoint streaming snapshots every 2 seconds
  - HTTP REST endpoints for initial data load
  - Background scheduler for all data feed refresh cycles
  - Graceful startup/shutdown

Run: uvicorn main:app --reload --port 8000
"""

import asyncio
import json
import logging
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from hub import hub
from snapshot import build_snapshot
from feeds import datafeed, eia_feed, steo_feed, cot_feed, twelvedata_feed, news_feed, hurricane_feed, ais_feed
import persistence

# ── Logging setup ─────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(name)-24s | %(levelname)-5s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("otd.main")

# ── WebSocket client registry ─────────────────────────────────
ws_clients: set[WebSocket] = set()

# ── Background task handles ───────────────────────────────────
_background_tasks: list[asyncio.Task] = []


# ── Scheduled feed loops ──────────────────────────────────────

async def _loop(name: str, interval: float, coro_fn):
    """Generic scheduled loop: run coro_fn every `interval` seconds."""
    logger.info(f"Scheduler: {name} every {interval}s")
    while True:
        try:
            await coro_fn()
        except Exception as e:
            logger.error(f"Scheduler {name} error: {e}")
        await asyncio.sleep(interval)


async def _snapshot_loop():
    """Push snapshots to all connected WebSocket clients every 2 seconds."""
    while True:
        if ws_clients:
            try:
                snapshot = build_snapshot()
                payload = json.dumps(snapshot, default=str)
                disconnected = set()
                for ws in ws_clients:
                    try:
                        await ws.send_text(payload)
                    except Exception:
                        disconnected.add(ws)
                ws_clients -= disconnected
                if disconnected:
                    logger.debug(f"Removed {len(disconnected)} disconnected client(s)")
            except Exception as e:
                logger.error(f"Snapshot broadcast error: {e}")
        await asyncio.sleep(config.CADENCE_SNAPSHOT_PUSH)


async def _bootstrap():
    """
    Initial data bootstrap at startup.
    Fetches all data sources once before starting the regular loops.
    """
    logger.info("Loading persistence state...")
    persistence.load_state()

    logger.info("=" * 60)
    logger.info("OIL TRADING DESK — BACKEND STARTING")
    logger.info("=" * 60)

    # Log configuration status
    logger.info(f"EIA API Key:        {'✓ configured' if config.HAS_EIA_KEY else '✗ not set (synthetic mode)'}")
    logger.info(f"Twelve Data Key:    {'✓ configured' if config.HAS_TWELVE_DATA_KEY else '✗ not set (yfinance fallback)'}")
    logger.info(f"AIS API Key:        {'✓ configured' if config.HAS_AIS_KEY else '✗ not set (disabled)'}")
    logger.info("-" * 60)

    # Bootstrap in priority order
    logger.info("Phase 1: Yahoo Finance prices + history + curve...")
    await datafeed.bootstrap()

    logger.info("Phase 2: EIA fundamentals...")
    await eia_feed.fetch_fundamentals()

    logger.info("Phase 3: STEO global balance...")
    await steo_feed.fetch_steo()

    logger.info("Phase 4: CFTC COT positioning...")
    await cot_feed.fetch_cot()

    logger.info("Phase 5: Twelve Data DXY...")
    await twelvedata_feed.fetch_dxy()

    logger.info("Phase 6: RSS news aggregation...")
    await news_feed.fetch_news()

    logger.info("Phase 7: NOAA hurricanes...")
    await hurricane_feed.fetch_hurricanes()

    logger.info("=" * 60)
    logger.info("BOOTSTRAP COMPLETE — All feeds initialized")
    logger.info(f"Feed status: {sum(1 for f in hub.feed_status.values() if f.healthy)}/{len(hub.feed_status)} healthy")
    logger.info("=" * 60)


# ── Lifespan (startup + shutdown) ─────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: bootstrap data, start schedulers, cleanup on shutdown."""

    # Bootstrap all data
    await _bootstrap()

    # Start scheduled loops
    tasks = [
        asyncio.create_task(_snapshot_loop()),
        asyncio.create_task(ais_feed.fetch_ais_stream()),
        asyncio.create_task(_loop("prices", config.CADENCE_PRICES, datafeed.fetch_prices)),
        asyncio.create_task(_loop("curve", config.CADENCE_CURVE, datafeed.fetch_curve)),
        asyncio.create_task(_loop("dxy", config.CADENCE_DXY_FOREX, twelvedata_feed.fetch_dxy)),
        asyncio.create_task(_loop("eia", config.CADENCE_EIA, eia_feed.fetch_fundamentals)),
        asyncio.create_task(_loop("steo", config.CADENCE_STEO, steo_feed.fetch_steo)),
        asyncio.create_task(_loop("cot", config.CADENCE_COT, cot_feed.fetch_cot)),
        asyncio.create_task(_loop("news", config.CADENCE_NEWS_RSS, news_feed.fetch_news)),
        asyncio.create_task(_loop("analyst_news", config.CADENCE_NEWS_ANALYST, news_feed.fetch_analyst_news)),
        asyncio.create_task(_loop("hurricanes", config.CADENCE_HURRICANE, hurricane_feed.fetch_hurricanes)),
        asyncio.create_task(_loop("history", config.CADENCE_HISTORY, datafeed.fetch_history)),
        asyncio.create_task(_loop("five_year", config.CADENCE_FIVE_YEAR, datafeed.fetch_5y_same_week)),
    ]
    _background_tasks.extend(tasks)
    logger.info(f"Started {len(tasks)} background scheduler tasks")

    yield  # App is running

    # Shutdown: cancel all tasks
    logger.info("Shutting down background tasks...")
    for task in _background_tasks:
        task.cancel()
    await asyncio.gather(*_background_tasks, return_exceptions=True)
    logger.info("Backend shutdown complete.")


# ── FastAPI app ───────────────────────────────────────────────

app = FastAPI(
    title="Oil Trading Desk API",
    description="Real-time oil market data backend for the Oil Market Intelligence Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST Endpoints ────────────────────────────────────────────

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Oil Trading Desk Backend",
        "status": "running",
        "uptime": round(hub.get_uptime(), 1),
        "feeds": {
            k: {"healthy": v.healthy, "synthetic": v.synthetic}
            for k, v in hub.feed_status.items()
        },
        "ws_clients": len(ws_clients),
    }


@app.get("/api/snapshot")
async def get_snapshot():
    """
    HTTP endpoint for initial data load.
    Returns the same JSON as the WebSocket stream.
    Useful for SSR or when WebSocket is not available.
    """
    snapshot = build_snapshot()
    return JSONResponse(content=snapshot)


@app.get("/api/status")
async def get_status():
    """Detailed status of all data feeds."""
    return {
        "uptime": round(hub.get_uptime(), 1),
        "ws_clients": len(ws_clients),
        "last_snapshot": hub.last_snapshot,
        "feeds": {
            k: {
                "name": v.name,
                "healthy": v.healthy,
                "last_update": v.last_update,
                "error": v.error,
                "synthetic": v.synthetic,
            }
            for k, v in hub.feed_status.items()
        },
    }


# ── WebSocket Endpoint ────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data streaming.

    The client connects and immediately receives snapshots every 2 seconds.
    No subscription message is needed — all clients get the full snapshot.
    """
    await websocket.accept()
    ws_clients.add(websocket)
    client_id = id(websocket)
    logger.info(f"WebSocket client connected (id={client_id}, total={len(ws_clients)})")

    # Send initial snapshot immediately
    try:
        snapshot = build_snapshot()
        await websocket.send_text(json.dumps(snapshot, default=str))
    except Exception as e:
        logger.warning(f"Failed to send initial snapshot: {e}")

    # Keep connection alive
    try:
        while True:
            # Listen for client messages (keepalive pings, etc.)
            data = await websocket.receive_text()
            # Client can send "ping" for keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"WebSocket error: {e}")
    finally:
        ws_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected (id={client_id}, total={len(ws_clients)})")


# ── Direct run ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level=config.LOG_LEVEL.lower(),
    )
