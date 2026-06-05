"""
Oil Trading Desk — Seasonality Analytics

Computes the 5-year seasonal average and standard deviation for EIA refinery utilization.
Identifies the current seasonal phase based on the week of the year.
"""

import numpy as np
import logging
from datetime import datetime
from hub import hub

logger = logging.getLogger("otd.analytics.seasonality")

# Defined seasonal phases for US refineries
SEASONAL_PHASES = [
    {"phase": "Heating Peak", "start_week": 1, "end_week": 6},
    {"phase": "Spring Turnaround", "start_week": 7, "end_week": 16},
    {"phase": "Pre-driving Build", "start_week": 17, "end_week": 21},
    {"phase": "Summer Driving", "start_week": 22, "end_week": 35},
    {"phase": "Fall Turnaround", "start_week": 36, "end_week": 44},
    {"phase": "Winter Prep", "start_week": 45, "end_week": 52},
]


def _get_phase(week: int) -> str:
    """Return the seasonal phase name for a given week of the year."""
    for p in SEASONAL_PHASES:
        if p["start_week"] <= week <= p["end_week"]:
            return p["phase"]
    return "Heating Peak"  # fallback for week 53


def update_seasonality():
    """
    Compute seasonality metrics from 5y EIA refinery utilization history
    and write to hub.seasonality.
    """
    history = hub.inventory_history.get("refineryUtil", [])
    if not history:
        # Fallback to checking crude history if refinery history isn't populated properly
        history = hub.inventory_history.get("crude", [])
        if not history:
            return

    # Assuming history contains objects with 'date' and 'value'
    # We group by ISO week of year (1-53)
    weekly_values = {i: [] for i in range(1, 54)}
    
    for item in history:
        try:
            # Handle YYYY-MM-DD or other formats
            date_str = item.get("date", "")
            if not date_str:
                continue
            
            # Simple parsing (assuming YYYY-MM-DD or similar)
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            week = dt.isocalendar()[1]
            val = float(item.get("value", 0))
            if val > 0:
                weekly_values[week].append(val)
        except Exception:
            continue

    # Calculate mean and std for each week
    seasonal_curve = []
    for week in range(1, 54):
        vals = weekly_values[week]
        if vals:
            mean = float(np.mean(vals))
            std = float(np.std(vals))
        else:
            mean = 0.0
            std = 0.0
            
        seasonal_curve.append({
            "week": week,
            "mean": mean,
            "std": std,
            "phase": _get_phase(week)
        })

    # Get current state
    current_week = datetime.now().isocalendar()[1]
    current_phase = _get_phase(current_week)
    
    # Next phase
    next_phase = current_phase
    for i in range(1, 10):
        test_week = ((current_week - 1 + i) % 52) + 1
        ph = _get_phase(test_week)
        if ph != current_phase:
            next_phase = ph
            break

    # Current expected value
    current_expected = seasonal_curve[current_week - 1] if 1 <= current_week <= 53 else seasonal_curve[0]

    hub.seasonality = {
        "currentWeek": current_week,
        "currentPhase": current_phase,
        "nextPhase": next_phase,
        "expectedMean": current_expected["mean"],
        "expectedStd": current_expected["std"],
        "curve": seasonal_curve
    }
    
    logger.debug(f"Seasonality updated: Week {current_week} ({current_phase})")
