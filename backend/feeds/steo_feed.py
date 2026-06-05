"""
Oil Trading Desk — EIA STEO Data Feed

Fetches global oil supply/demand balance from EIA Short-Term Energy Outlook.
6 monthly series for world supply, demand, OPEC, non-OPEC, OECD, non-OECD.

Series:
  STEO.PAPR_WORLD.M    — World oil production
  STEO.PATC_WORLD.M    — World oil consumption
  STEO.PAPR_OPEC.M     — OPEC production
  STEO.PAPR_NONOPEC.M  — Non-OPEC production
  STEO.PATC_OECD.M     — OECD consumption
  STEO.PATC_NON_OECD.M — Non-OECD consumption
"""

import logging

import httpx

from config import EIA_API_KEY, HAS_EIA_KEY
from hub import hub
from utils.helpers import safe_float

logger = logging.getLogger("otd.feeds.steo")

STEO_BASE = "https://api.eia.gov/v2/steo"

STEO_SERIES = {
    "supply_world": "PAPR_WORLD",
    "demand_world": "PATC_WORLD",
    "supply_opec": "PAPR_OPEC",
    "supply_nonopec": "PAPR_NONOPEC",
    "demand_oecd": "PATC_OECD",
    "demand_nonoecd": "PATC_NON_OECD",
}


async def _fetch_steo_series(client: httpx.AsyncClient, series_id: str) -> list[dict]:
    """Fetch a single STEO series."""
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "monthly",
        "data[0]": "value",
        "facets[seriesId][]": series_id,
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": "36",  # 3 years for historical + forecast view
    }
    resp = await client.get(f"{STEO_BASE}/data", params=params, timeout=15.0)
    resp.raise_for_status()
    body = resp.json()
    return body.get("response", {}).get("data", [])


async def fetch_steo():
    """
    Fetch all 6 STEO series and compute supply-demand balance.
    Updates hub.steo with monthly balance data.
    """
    if not HAS_EIA_KEY:
        logger.warning("EIA_API_KEY not set — STEO disabled")
        hub.update_feed_status("steo", False, "No API key", synthetic=True)
        return

    async with httpx.AsyncClient() as client:
        try:
            raw = {}
            for key, series_id in STEO_SERIES.items():
                try:
                    data = await _fetch_steo_series(client, series_id)
                    raw[key] = data
                except Exception as e:
                    logger.warning(f"STEO series {key} failed: {e}")
                    raw[key] = []

            # Build supply-demand balance
            supply_data = {r["period"]: safe_float(r.get("value")) for r in raw.get("supply_world", [])}
            demand_data = {r["period"]: safe_float(r.get("value")) for r in raw.get("demand_world", [])}

            balance = []
            all_periods = sorted(set(supply_data.keys()) & set(demand_data.keys()))
            for period in all_periods:
                s = supply_data[period]
                d = demand_data[period]
                balance.append({
                    "period": period,
                    "supply": round(s, 2),
                    "demand": round(d, 2),
                    "balance": round(s - d, 2),
                })

            # Latest values for each series
            latest = {}
            for key, data in raw.items():
                if data:
                    latest[key] = {
                        "value": round(safe_float(data[0].get("value")), 2),
                        "period": data[0].get("period", ""),
                    }

            hub.steo = {
                "latest": latest,
                "balance": balance[-24:],  # Last 2 years
            }
            hub.update_feed_status("steo", True)
            logger.info(f"STEO updated: {len(balance)} balance records")

        except Exception as e:
            hub.update_feed_status("steo", False, str(e))
            logger.error(f"STEO fetch error: {e}")
