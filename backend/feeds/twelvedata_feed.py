"""
Oil Trading Desk — Twelve Data DXY Reconstruction Feed

Reconstructs the ICE US Dollar Index from 6 forex component pairs.
Falls back to Yahoo Finance DX-Y.NYB if no API key is available.

ICE DXY Formula:
  50.14348112 × EUR/USD^-0.576 × USD/JPY^+0.136 × GBP/USD^-0.119
                × USD/CAD^+0.091 × USD/SEK^+0.042 × USD/CHF^+0.036

Free tier: 800 credits/day; each batched price call = 1 credit.
At 5-min cadence: 288 calls/day (well within limit).
"""

import logging

import httpx

from config import TWELVE_DATA_API_KEY, HAS_TWELVE_DATA_KEY
from hub import hub
from utils.helpers import safe_float

logger = logging.getLogger("otd.feeds.twelvedata")

TWELVE_DATA_URL = "https://api.twelvedata.com/price"

# ICE DXY component weights (exponents)
DXY_COMPONENTS = {
    "EUR/USD": -0.576,
    "USD/JPY": 0.136,
    "GBP/USD": -0.119,
    "USD/CAD": 0.091,
    "USD/SEK": 0.042,
    "USD/CHF": 0.036,
}

DXY_CONSTANT = 50.14348112


def _compute_dxy(rates: dict[str, float]) -> float:
    """
    Compute the ICE DXY index value from 6 forex pair rates.
    Formula: 50.14348112 × ∏(pair^weight)
    """
    result = DXY_CONSTANT
    for pair, weight in DXY_COMPONENTS.items():
        rate = rates.get(pair)
        if rate is None or rate <= 0:
            return 0.0
        result *= rate ** weight
    return round(result, 3)


async def fetch_dxy():
    """
    Fetch 6 forex pairs from Twelve Data and reconstruct the DXY index.
    Updates hub.dxy_value, hub.dxy_source.
    """
    if not HAS_TWELVE_DATA_KEY:
        logger.debug("Twelve Data key not set — DXY from yfinance fallback")
        hub.update_feed_status("twelvedata", False, "No API key", synthetic=True)
        return

    async with httpx.AsyncClient() as client:
        try:
            # Batch request for all 6 pairs
            symbols = ",".join(DXY_COMPONENTS.keys())
            params = {
                "symbol": symbols,
                "apikey": TWELVE_DATA_API_KEY,
            }
            resp = await client.get(TWELVE_DATA_URL, params=params, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()

            # Parse rates
            rates = {}
            for pair in DXY_COMPONENTS:
                pair_data = data.get(pair, {})
                price = safe_float(pair_data.get("price"))
                if price > 0:
                    rates[pair] = price

            if len(rates) < 6:
                hub.update_feed_status("twelvedata", False, f"Only {len(rates)}/6 pairs returned")
                return

            dxy = _compute_dxy(rates)
            if dxy > 0:
                # Calculate change from previous value
                prev = hub.dxy_value if hub.dxy_value > 0 else dxy
                change = round(dxy - prev, 3)

                hub.dxy_value = dxy
                hub.dxy_change = change
                hub.dxy_source = "twelvedata"
                hub.update_feed_status("twelvedata", True)
                logger.info(f"DXY reconstructed: {dxy:.3f} (chg {change:+.3f})")
            else:
                hub.update_feed_status("twelvedata", False, "DXY computation returned 0")

        except Exception as e:
            hub.update_feed_status("twelvedata", False, str(e))
            logger.error(f"Twelve Data fetch error: {e}")
