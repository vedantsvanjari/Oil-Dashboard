"""
Oil Trading Desk — CFTC COT Data Feed

Fetches Commitments of Traders positioning data from the CFTC Socrata API.
Filters to NYMEX WTI (contract code 067411).

Endpoint: https://publicreporting.cftc.gov/resource/gpe5-46if.json
No authentication required.
"""

import logging

import httpx

from hub import hub
from utils.helpers import safe_float, safe_int

logger = logging.getLogger("otd.feeds.cot")

CFTC_URL = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
WTI_CONTRACT_CODE = "067411"


async def fetch_cot():
    """
    Fetch latest CFTC COT data for NYMEX WTI.
    Extracts managed money, commercial, and swap dealer positioning.
    """
    async with httpx.AsyncClient() as client:
        try:
            params = {
                "cftc_contract_market_code": WTI_CONTRACT_CODE,
                "$order": "report_date_as_yyyy_mm_dd DESC",
                "$limit": "2",  # Current + previous for week-over-week change
            }
            resp = await client.get(CFTC_URL, params=params, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

            if not data:
                hub.update_feed_status("cot", False, "No data returned")
                return

            latest = data[0]
            prev = data[1] if len(data) >= 2 else data[0]

            # Managed money (hedge funds + CTAs)
            mm_long = safe_int(latest.get("m_money_positions_long_all"))
            mm_short = safe_int(latest.get("m_money_positions_short_all"))
            mm_net = mm_long - mm_short

            prev_mm_long = safe_int(prev.get("m_money_positions_long_all"))
            prev_mm_short = safe_int(prev.get("m_money_positions_short_all"))
            prev_mm_net = prev_mm_long - prev_mm_short

            net_change = mm_net - prev_mm_net

            # Commercial (producers + merchants)
            comm_long = safe_int(latest.get("comm_positions_long_all"))
            comm_short = safe_int(latest.get("comm_positions_short_all"))
            comm_net = comm_long - comm_short

            # Swap dealers
            swap_long = safe_int(latest.get("swap_positions_long_all"))
            swap_short = safe_int(latest.get("swap_positions_short_all"))
            swap_net = swap_long - swap_short

            hub.cot = {
                "report_date": latest.get("report_date_as_yyyy_mm_dd", ""),
                "managed_money": {
                    "long": mm_long,
                    "short": mm_short,
                    "net": mm_net,
                    "net_change": net_change,
                },
                "commercial": {
                    "long": comm_long,
                    "short": comm_short,
                    "net": comm_net,
                },
                "swap_dealer": {
                    "long": swap_long,
                    "short": swap_short,
                    "net": swap_net,
                },
                "open_interest": safe_int(latest.get("open_interest_all")),
            }
            hub.update_feed_status("cot", True)
            logger.info(f"COT updated: MM net={mm_net:+,d} (chg {net_change:+,d})")

        except Exception as e:
            hub.update_feed_status("cot", False, str(e))
            logger.error(f"CFTC COT fetch error: {e}")
