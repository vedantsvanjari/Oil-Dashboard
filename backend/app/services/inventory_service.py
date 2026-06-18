import os
import logging
import threading
import requests
from datetime import datetime, timezone
from cachetools import TTLCache, cached
from sqlalchemy.orm import Session
from app.models.inventories import Inventory

logger = logging.getLogger(__name__)

EIA_API_KEY = os.getenv("EIA_API_KEY", "")

FACET_MAP = {
    "crude": "&facets[duoarea][]=NUS&facets[product][]=EPC0&facets[process][]=SAX",
    "gasoline": "&facets[duoarea][]=NUS&facets[product][]=EPM0&facets[process][]=SAE",
    "distillate": "&facets[duoarea][]=NUS&facets[product][]=EPD0&facets[process][]=SAE",
    "spr": "&facets[duoarea][]=NUS&facets[product][]=EPC0&facets[process][]=SAS"
}

# EIA inventory data is weekly, so caching for several minutes avoids hammering the
# API on rapid dashboard refreshes. Locks guard concurrent threadpool access.
_LATEST_CACHE = TTLCache(maxsize=1, ttl=900)       # 15 min
_LATEST_LOCK = threading.Lock()
_HIST_CACHE = TTLCache(maxsize=1, ttl=3600)        # 1 hour
_HIST_LOCK = threading.Lock()

# Default request timeout (seconds) so a hung EIA endpoint can't tie up a worker.
_HTTP_TIMEOUT = 15


def _fetch_eia_latest_external() -> dict:
    """Fetch the latest EIA inventory snapshot (no DB, no caching)."""
    result = {"crude": 0.0, "gasoline": 0.0, "distillate": 0.0, "spr": 0.0, "date": None}

    if not EIA_API_KEY:
        logger.warning("EIA_API_KEY is not set. Using mocked inventory data.")
        return {
            "crude": 420.5, "gasoline": 215.3, "distillate": 110.2, "spr": 350.0,
            "date": datetime.now(timezone.utc).isoformat(),
        }

    try:
        latest_date_str = None
        for key, facets in FACET_MAP.items():
            url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value{facets}&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1"
            response = requests.get(url, timeout=_HTTP_TIMEOUT)
            logger.debug("EIA latest %s -> %s", key, response.status_code)
            response.raise_for_status()
            data = response.json()

            if "response" in data and "data" in data["response"] and len(data["response"]["data"]) > 0:
                latest = data["response"]["data"][0]
                result[key] = float(latest.get("value", 0.0))

                if latest_date_str is None:
                    period = latest.get("period", "")
                    if period:
                        try:
                            dt = datetime.strptime(period, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                            latest_date_str = dt.isoformat()
                        except ValueError as e:
                            logger.warning("Could not parse EIA period '%s': %s", period, e)

        result["date"] = latest_date_str or datetime.now(timezone.utc).isoformat()
    except Exception as e:
        logger.error("Error fetching EIA data: %s", e)
        result["date"] = datetime.now(timezone.utc).isoformat()

    return result


def fetch_eia_inventories(db: Session = None):
    """Return latest EIA inventories, cached for the TTL window. Persists only on a
    cache miss so repeated refreshes avoid redundant HTTP and DB writes."""
    with _LATEST_LOCK:
        cached_result = _LATEST_CACHE.get("latest")
        if cached_result is not None:
            return cached_result

        result = _fetch_eia_latest_external()
        _persist_inventories(db, result)
        _LATEST_CACHE["latest"] = result
        return result


def _persist_inventories(db: Session, result: dict) -> None:
    if not db:
        return
    try:
        dt = datetime.fromisoformat(result["date"]) if result.get("date") else datetime.now(timezone.utc)
        for key in ["crude", "gasoline", "distillate", "spr"]:
            existing = db.query(Inventory).filter(Inventory.item_name == key, Inventory.date == dt).first()
            if existing:
                existing.quantity = result[key]
            else:
                db.add(Inventory(item_name=key, quantity=result[key], date=dt))
        db.commit()
    except Exception as e:
        logger.error("Error saving inventory to DB: %s", e)
        db.rollback()


@cached(_HIST_CACHE, lock=_HIST_LOCK)
def fetch_historical_inventories():
    if not EIA_API_KEY:
        logger.warning("EIA_API_KEY is not set. Using mocked historical inventory data.")
        return [
            {"date": "2024-10-18", "crude": 420.5, "gasoline": 215.3, "distillate": 110.2, "spr": 350.0},
            {"date": "2024-10-11", "crude": 422.1, "gasoline": 212.1, "distillate": 112.5, "spr": 350.0},
            {"date": "2024-10-04", "crude": 418.9, "gasoline": 214.0, "distillate": 113.8, "spr": 350.0},
            {"date": "2024-09-27", "crude": 415.0, "gasoline": 211.5, "distillate": 114.5, "spr": 350.0},
            {"date": "2024-09-20", "crude": 412.0, "gasoline": 209.5, "distillate": 115.5, "spr": 350.0},
        ]

    history = {}
    try:
        for key, facets in FACET_MAP.items():
            url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/?api_key={EIA_API_KEY}&frequency=weekly&data[0]=value{facets}&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=52"
            response = requests.get(url, timeout=_HTTP_TIMEOUT)
            logger.debug("EIA history %s -> %s", key, response.status_code)
            response.raise_for_status()
            data = response.json()

            if "response" in data and "data" in data["response"]:
                for row in data["response"]["data"]:
                    period = row.get("period", "")
                    if period:
                        if period not in history:
                            history[period] = {"date": period, "crude": 0.0, "gasoline": 0.0, "distillate": 0.0, "spr": 0.0}
                        history[period][key] = float(row.get("value", 0.0))

        return sorted(list(history.values()), key=lambda x: x["date"], reverse=True)
    except Exception as e:
        logger.error("Error fetching historical EIA data: %s", e)
        return []
