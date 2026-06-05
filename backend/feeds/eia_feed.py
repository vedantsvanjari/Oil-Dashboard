"""
Oil Trading Desk — EIA v2 API Data Feed

Fetches US crude oil fundamentals from the EIA v2 REST API.
7 series batched in parallel using httpx async client.

Series:
  PET.WCESTUS1.W             — US crude stocks (weekly)
  PET.W_EPC0_SAX_YCUOK_MBBL.W — Cushing inventory (weekly)
  PET.WPULEUS3.W             — Refinery utilization (weekly)
  PET.WCRFPUS2.W             — US crude production (weekly)
  PET.W_EPM0F_SAE_NUS_MBBL.W — US gasoline stocks (weekly)
  PET.E_ERTRR0_XR0_NUS_C.M  — Rig count (monthly)

Requires: EIA_API_KEY environment variable.
"""

import asyncio
import logging
from datetime import datetime

import httpx

from config import EIA_API_KEY, HAS_EIA_KEY
from hub import hub
from utils.helpers import safe_float, safe_int

logger = logging.getLogger("otd.feeds.eia")

EIA_BASE = "https://api.eia.gov/v2/seriesid"

# ── Series definitions ────────────────────────────────────────
SERIES = {
    "crude_stocks": {
        "id": "PET.WCESTUS1.W",
        "label": "US Crude Stocks",
        "unit": "mn bbl",
        "frequency": "weekly",
        "length": 52,
    },
    "cushing": {
        "id": "PET.W_EPC0_SAX_YCUOK_MBBL.W",
        "label": "Cushing Stocks",
        "unit": "mn bbl",
        "frequency": "weekly",
        "length": 52,
    },
    "refinery_util": {
        "id": "PET.WPULEUS3.W",
        "label": "Refinery Utilization",
        "unit": "%",
        "frequency": "weekly",
        "length": 52,
    },
    "production": {
        "id": "PET.WCRFPUS2.W",
        "label": "US Crude Production",
        "unit": "kbpd",
        "frequency": "weekly",
        "length": 52,
    },
    "gasoline_stocks": {
        "id": "PET.W_EPM0F_SAE_NUS_MBBL.W",
        "label": "Gasoline Stocks",
        "unit": "mn bbl",
        "frequency": "weekly",
        "length": 52,
    },
    "rig_count": {
        "id": "PET.E_ERTRR0_XR0_NUS_C.M",
        "label": "Rig Count",
        "unit": "",
        "frequency": "monthly",
        "length": 12,
    },
}

# 5-year refinery utilization for seasonality
REFINERY_HIST_SERIES = "PET.WPULEUS3.W"
REFINERY_HIST_LENGTH = 260  # 5 years × 52 weeks


async def _fetch_series(client: httpx.AsyncClient, series_id: str, length: int = 1) -> list[dict]:
    """Fetch a single EIA series and return the data records."""
    params = {
        "api_key": EIA_API_KEY,
        "frequency": "weekly",
        "data[0]": "value",
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length": str(length),
    }
    url = f"{EIA_BASE}/{series_id}"
    resp = await client.get(url, params=params, timeout=15.0)
    resp.raise_for_status()
    body = resp.json()

    data = body.get("response", {}).get("data", [])
    return data


async def _fetch_series_history(client: httpx.AsyncClient, series_id: str, length: int = 260) -> list[dict]:
    """Fetch historical data for inventory charting with 5-year bands."""
    return await _fetch_series(client, series_id, length)


def _compute_inventory_chart(records: list[dict]) -> list[dict]:
    """
    From raw EIA weekly records, compute the chart data with
    5-year average, min, and max bands.
    """
    if not records:
        return []

    # Sort chronologically
    sorted_records = sorted(records, key=lambda r: r.get("period", ""))

    # Group by week-of-year for 5-year statistics
    week_data = {}
    for rec in sorted_records:
        try:
            date = datetime.strptime(rec["period"], "%Y-%m-%d")
            week_num = date.isocalendar()[1]
            value = safe_float(rec.get("value"))
            year = date.year
            if week_num not in week_data:
                week_data[week_num] = {}
            week_data[week_num][year] = value
        except (ValueError, KeyError):
            continue

    # Build chart records for the most recent year
    chart_data = []
    current_year = datetime.now().year
    for rec in sorted_records:
        try:
            date = datetime.strptime(rec["period"], "%Y-%m-%d")
            if date.year < current_year - 1:
                continue
            week_num = date.isocalendar()[1]
            value = safe_float(rec.get("value"))

            # Get historical values for this week (excluding current year)
            hist_values = [
                v for yr, v in week_data.get(week_num, {}).items()
                if yr != current_year and yr != current_year - 1
            ]

            chart_data.append({
                "date": rec["period"],
                "value": round(value, 1),
                "fiveYearAvg": round(sum(hist_values) / len(hist_values), 1) if hist_values else round(value, 1),
                "fiveYearMin": round(min(hist_values), 1) if hist_values else round(value * 0.9, 1),
                "fiveYearMax": round(max(hist_values), 1) if hist_values else round(value * 1.1, 1),
            })
        except (ValueError, KeyError):
            continue

    return chart_data[-52:]  # Last 52 weeks


async def fetch_fundamentals():
    """
    Fetch all EIA fundamental series in parallel and update hub.
    Uses a single httpx client with concurrent requests for efficiency.
    """
    if not HAS_EIA_KEY:
        logger.warning("EIA_API_KEY not set — using synthetic fundamentals")
        hub.update_feed_status("eia", False, "No API key", synthetic=True)
        _apply_synthetic_fundamentals()
        return

    async with httpx.AsyncClient() as client:
        try:
            # Fetch all series concurrently
            tasks = {}
            for key, series_def in SERIES.items():
                tasks[key] = _fetch_series(client, series_def["id"], series_def["length"])

            # Also fetch crude stock history for chart
            tasks["crude_hist"] = _fetch_series_history(client, SERIES["crude_stocks"]["id"], 260)
            tasks["cushing_hist"] = _fetch_series_history(client, SERIES["cushing"]["id"], 260)
            tasks["gasoline_hist"] = _fetch_series_history(client, SERIES["gasoline_stocks"]["id"], 260)

            results = {}
            for key, coro in tasks.items():
                try:
                    results[key] = await coro
                except Exception as e:
                    logger.warning(f"EIA series {key} failed: {e}")
                    results[key] = []

            # Process latest values
            fundamentals = {}
            for key, series_def in SERIES.items():
                data = results.get(key, [])
                if data:
                    latest = data[0]
                    prev = data[1] if len(data) >= 2 else data[0]
                    value = safe_float(latest.get("value"))
                    prev_value = safe_float(prev.get("value"))
                    change = round(value - prev_value, 2)

                    fundamentals[key] = {
                        "label": series_def["label"],
                        "value": round(value, 1),
                        "unit": series_def["unit"],
                        "weekChange": change,
                        "period": latest.get("period", ""),
                    }

            # Compute inventory chart data
            inventory_history = {}
            for hist_key in ["crude_hist", "cushing_hist", "gasoline_hist"]:
                chart_key = hist_key.replace("_hist", "")
                data = results.get(hist_key, [])
                if data:
                    inventory_history[chart_key] = _compute_inventory_chart(data)

            hub.fundamentals = fundamentals
            hub.inventory_history = inventory_history
            hub.update_feed_status("eia", True)
            logger.info(f"EIA fundamentals updated: {list(fundamentals.keys())}")

        except Exception as e:
            hub.update_feed_status("eia", False, str(e))
            logger.error(f"EIA fetch error: {e}")


def _apply_synthetic_fundamentals():
    """Apply hardcoded fallback values matching the frontend mock data."""
    hub.fundamentals = {
        "crude_stocks": {
            "label": "US Crude Stocks",
            "value": 430.2,
            "unit": "mn bbl",
            "weekChange": -2.4,
            "period": "",
        },
        "cushing": {
            "label": "Cushing Stocks",
            "value": 24.8,
            "unit": "mn bbl",
            "weekChange": -0.8,
            "period": "",
        },
        "refinery_util": {
            "label": "Refinery Utilization",
            "value": 91.2,
            "unit": "%",
            "weekChange": 0.4,
            "period": "",
        },
        "production": {
            "label": "US Crude Production",
            "value": 13200,
            "unit": "kbpd",
            "weekChange": 0,
            "period": "",
        },
        "gasoline_stocks": {
            "label": "Gasoline Stocks",
            "value": 228.4,
            "unit": "mn bbl",
            "weekChange": -1.2,
            "period": "",
        },
        "rig_count": {
            "label": "Rig Count",
            "value": 588,
            "unit": "",
            "weekChange": -3,
            "period": "",
        },
    }
