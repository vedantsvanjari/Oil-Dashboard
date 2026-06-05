"""
Oil Trading Desk — Configuration & Environment Loading

Loads API keys from .env and defines refresh cadences for all data feeds.
When keys are missing, feeds fall back to synthetic data gracefully.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env from backend directory ──────────────────────────
_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path)

# ── API Keys ──────────────────────────────────────────────────
EIA_API_KEY: str = os.getenv("EIA_API_KEY", "")
TWELVE_DATA_API_KEY: str = os.getenv("TWELVE_DATA_API_KEY", "")
AIS_API_KEY: str = os.getenv("AIS_API_KEY", "")
HF_TOKEN: str = os.getenv("HF_TOKEN", "")
PAPER_STATE_REPO: str = os.getenv("PAPER_STATE_REPO", "")

# ── Key availability flags ────────────────────────────────────
HAS_EIA_KEY = bool(EIA_API_KEY) and EIA_API_KEY != "your_eia_api_key_here"
HAS_TWELVE_DATA_KEY = bool(TWELVE_DATA_API_KEY) and TWELVE_DATA_API_KEY != "your_twelve_data_key_here"
HAS_AIS_KEY = bool(AIS_API_KEY) and AIS_API_KEY != "your_ais_api_key_here"

# ── Refresh cadences (seconds) ────────────────────────────────
# These match the TECHNICAL.md master schedule
CADENCE_PRICES = 60          # WTI/Brent/RBOB/HO spot prices
CADENCE_CURVE = 60           # 12-month NYMEX futures curve
CADENCE_DXY_FOREX = 300      # Twelve Data DXY forex pairs (5 min)
CADENCE_NEWS_RSS = 16         # RSS feeds (4 sources)
CADENCE_NEWS_ANALYST = 900    # Google News analyst feeds (15 min)
CADENCE_EIA = 1800            # EIA fundamentals (30 min)
CADENCE_STEO = 3600           # EIA STEO global S/D (60 min)
CADENCE_COT = 1800            # CFTC COT positioning (30 min)
CADENCE_HURRICANE = 600       # NOAA NHC storms (10 min)
CADENCE_HISTORY = 21600       # 1-year price history refresh (6h)
CADENCE_FIVE_YEAR = 21600     # 5-year range refresh (6h)
CADENCE_SNAPSHOT_PUSH = 2     # WebSocket snapshot to all clients

# ── Server settings ───────────────────────────────────────────
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
CORS_ORIGINS = [
    "http://localhost:5173",   # Vite dev server
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

# ── Logging ───────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
