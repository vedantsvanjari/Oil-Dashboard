"""
Oil Trading Desk — NOAA NHC Hurricane Tracking Feed

Fetches active Atlantic storm data from NOAA's National Hurricane Center.
Bloomberg uses the same endpoint.

Endpoint: https://www.nhc.noaa.gov/CurrentStorms.json
No authentication required. No documented rate limit.
"""

import logging

import httpx

from hub import hub

logger = logging.getLogger("otd.feeds.hurricane")

NHC_URL = "https://www.nhc.noaa.gov/CurrentStorms.json"


async def fetch_hurricanes():
    """
    Fetch active Atlantic storms from NOAA NHC.
    Filters to Atlantic basin (storm IDs starting with 'AL').
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(NHC_URL, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

            storms = []
            active_storms = data.get("activeStorms", [])

            for storm in active_storms:
                # Filter Atlantic basin only
                storm_id = storm.get("id", "")
                if not storm_id.upper().startswith("AL"):
                    continue

                storms.append({
                    "id": storm_id,
                    "name": storm.get("name", "Unknown"),
                    "classification": storm.get("classification", ""),
                    "intensity": storm.get("intensity", 0),
                    "pressure": storm.get("pressure", 0),
                    "lat": storm.get("lat", 0),
                    "lon": storm.get("lon", 0),
                    "movement": {
                        "direction": storm.get("movementDir", ""),
                        "speed": storm.get("movementSpeed", 0),
                    },
                    "advisory_url": storm.get("publicAdvisory", {}).get("url", ""),
                    "last_update": storm.get("lastUpdate", ""),
                })

            hub.storms = storms
            hub.update_feed_status("hurricane", True)

            if storms:
                logger.info(f"Hurricane data updated: {len(storms)} active Atlantic storms")
            else:
                logger.debug("No active Atlantic storms")

        except Exception as e:
            hub.update_feed_status("hurricane", False, str(e))
            logger.warning(f"NOAA NHC fetch error: {e}")
