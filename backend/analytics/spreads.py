"""
Oil Trading Desk — Spread Calculations

Computes calendar spreads, WTI-Brent spread, and crack spreads
from live price data in the hub.
"""

import logging

from hub import hub
from analytics.indicators import compute_spread_stats

logger = logging.getLogger("otd.analytics.spreads")


def compute_calendar_spreads() -> list[dict]:
    """
    Compute calendar spreads from the 12-month NYMEX futures curve.
    Returns M1-M2, M2-M3, M3-M4, M1-M12 spreads.
    """
    curve = hub.curve
    if len(curve) < 12:
        return []

    prices = [c["price"] for c in curve]

    spreads_def = [
        {"id": "m1m2", "name": "Brent M1-M2", "m1": 0, "m2": 1},
        {"id": "m2m3", "name": "Brent M2-M3", "m1": 1, "m2": 2},
        {"id": "m3m4", "name": "Brent M3-M4", "m1": 2, "m2": 3},
        {"id": "m1m12", "name": "Brent M1-M12", "m1": 0, "m2": 11},
    ]

    results = []
    for s_def in spreads_def:
        if s_def["m2"] >= len(prices):
            continue

        value = round(prices[s_def["m1"]] - prices[s_def["m2"]], 3)
        structure = "BACKWARDATION" if value > 0 else "CONTANGO" if value < 0 else "FLAT"

        # Historical spread values from curve history for statistics
        hist_values = []
        for snapshot in hub.curve_history:
            c = snapshot.get("curve", [])
            if len(c) > s_def["m2"]:
                hist_values.append(c[s_def["m1"]]["price"] - c[s_def["m2"]]["price"])

        stats = compute_spread_stats(hist_values) if hist_values else {"ma20": value, "zScore": 0, "percentile": 50}

        # Day change (from previous curve snapshot)
        day_change = 0.0
        if len(hub.curve_history) >= 2:
            prev_curve = list(hub.curve_history)[-2].get("curve", [])
            if len(prev_curve) > s_def["m2"]:
                prev_value = prev_curve[s_def["m1"]]["price"] - prev_curve[s_def["m2"]]["price"]
                day_change = round(value - prev_value, 3)

        results.append({
            "id": s_def["id"],
            "name": s_def["name"],
            "value": value,
            "structure": structure,
            "dayChange": day_change,
            "ma20": stats["ma20"],
            "zScore": stats["zScore"],
            "percentile": stats["percentile"],
            "series": [],  # Populated by snapshot builder from history
        })

    return results


def compute_wti_brent_spread() -> dict:
    """Compute WTI - Brent spread from spot prices."""
    prices = hub.prices
    wti_price = prices.get("wti", {}).get("price", 0)
    brent_price = prices.get("brent", {}).get("price", 0)

    if not wti_price or not brent_price:
        return {}

    value = round(wti_price - brent_price, 2)

    return {
        "id": "wtiBrent",
        "name": "WTI-Brent Spread",
        "value": value,
        "dayChange": 0,
        "ma20": value,
        "zScore": 0,
        "percentile": 50,
        "series": [],
    }


def compute_crack_spreads() -> dict:
    """
    Compute 3:2:1 crack spread.
    Formula: (2 × RBOB + 1 × HO) / 3 - WTI
    RBOB and HO are in $/gal, need to convert to $/bbl (× 42 gal/bbl).
    """
    prices = hub.prices
    wti = prices.get("wti", {}).get("price", 0)
    rbob = prices.get("rbob", {}).get("price", 0)
    ho = prices.get("heatingOil", {}).get("price", 0)

    if not all([wti, rbob, ho]):
        return {}

    # Convert products from $/gal to $/bbl
    rbob_bbl = rbob * 42
    ho_bbl = ho * 42

    # 3:2:1 crack
    crack_321 = round((2 * rbob_bbl + 1 * ho_bbl) / 3 - wti, 2)

    interpretation = ""
    if crack_321 > 25:
        interpretation = "Exceptional refining margins. Crack above $25/bbl signals extreme product tightness."
    elif crack_321 > 10:
        interpretation = f"${crack_321:.0f}/bbl = Normal refining margin. >$25 = Exceptional. Current level is healthy."
    else:
        interpretation = "Weak refining margins signal product oversupply or demand weakness."

    return {
        "id": "crack",
        "name": "3:2:1 Crack Spread",
        "value": crack_321,
        "dayChange": 0,
        "ma20": crack_321,
        "zScore": 0,
        "percentile": 50,
        "interpretation": interpretation,
        "series": [],
    }


def update_spreads():
    """Compute all spreads and update the hub."""
    hub.spreads = compute_calendar_spreads()
    hub.wti_brent_spread = compute_wti_brent_spread()
    hub.crack_spread = compute_crack_spreads()
