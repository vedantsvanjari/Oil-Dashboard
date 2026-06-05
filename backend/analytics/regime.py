"""
Oil Trading Desk — Regime Detection

Classifies the current market regime based on multiple signal dimensions:
- DXY-Brent correlation strength
- Calendar spread structure (backwardation depth)
- Inventory draw/build streak
- Crack spread deviation from MA

Five regimes:
  MACRO DRIVEN       — USD and rates dominate price action
  SUPPLY SHOCK       — Sudden supply disruption or OPEC action
  DEMAND SHOCK       — Demand destruction or recovery
  PHYSICAL TIGHTNESS — Inventory draws, backwardation, physical premiums
  REFINING DRIVEN    — Crack spreads and product markets leading
"""

import logging
from datetime import datetime

from hub import hub

logger = logging.getLogger("otd.analytics.regime")

REGIMES = [
    {"id": "macro", "label": "MACRO DRIVEN", "color": "#a855f7",
     "description": "Price driven by USD, rates, and risk sentiment"},
    {"id": "supply", "label": "SUPPLY SHOCK", "color": "#f97316",
     "description": "Sudden supply disruption or OPEC action driving prices"},
    {"id": "demand", "label": "DEMAND SHOCK", "color": "#06b6d4",
     "description": "Demand destruction or recovery dominating fundamentals"},
    {"id": "physical", "label": "PHYSICAL TIGHTNESS", "color": "#10b981",
     "description": "Inventory draws, backwardation, and physical premiums leading"},
    {"id": "refining", "label": "REFINING DRIVEN", "color": "#f59e0b",
     "description": "Crack spreads and product markets driving crude direction"},
]


def detect_regime() -> dict:
    """
    Analyze current market state and determine the active regime.
    Returns a regime dict matching the frontend's regimeData shape.
    """
    scores = {"macro": 0, "supply": 0, "demand": 0, "physical": 0, "refining": 0}

    # ── Signal 1: Calendar spread structure ────────────────────
    spreads = hub.spreads
    if spreads:
        m1m12 = next((s for s in spreads if s["id"] == "m1m12"), None)
        if m1m12:
            if m1m12["value"] > 2.0:
                scores["physical"] += 30  # Strong backwardation
            elif m1m12["value"] > 0.5:
                scores["physical"] += 15
            elif m1m12["value"] < -1.0:
                scores["demand"] += 20  # Deep contango = demand concern

    # ── Signal 2: Inventory trend ──────────────────────────────
    fundamentals = hub.fundamentals
    crude = fundamentals.get("crude_stocks", {})
    if crude:
        change = crude.get("weekChange", 0)
        if change < -2.0:
            scores["physical"] += 25  # Big draw
        elif change < 0:
            scores["physical"] += 10
        elif change > 3.0:
            scores["demand"] += 15  # Big build

    # ── Signal 3: DXY movement ─────────────────────────────────
    if hub.dxy_value > 0:
        dxy_change = hub.dxy_change
        if abs(dxy_change) > 0.5:
            scores["macro"] += 25  # Strong dollar move
        elif abs(dxy_change) > 0.2:
            scores["macro"] += 10

    # ── Signal 4: Crack spread ─────────────────────────────────
    crack = hub.crack_spread
    if crack:
        crack_val = crack.get("value", 0)
        if crack_val > 25:
            scores["refining"] += 30  # Exceptional cracks
        elif crack_val > 18:
            scores["refining"] += 15
        elif crack_val < 8:
            scores["demand"] += 10  # Weak cracks = weak product demand

    # ── Signal 5: News-driven geopolitical events ──────────────
    news = list(hub.news)
    geo_count = sum(1 for n in news[:20] if n.get("category") == "Geopolitics")
    if geo_count > 5:
        scores["supply"] += 25  # Heavy geopolitical flow
    elif geo_count > 2:
        scores["supply"] += 10

    # ── Signal 6: OPEC compliance/action ───────────────────────
    opec = hub.opec
    if opec:
        compliance = opec.get("compliancePercent", 0)
        if compliance > 98:
            scores["supply"] += 15  # High OPEC discipline
            scores["physical"] += 10

    # ── Determine winner ──────────────────────────────────────
    total = max(sum(scores.values()), 1)
    best_regime = max(scores, key=scores.get)
    confidence = min(95, int((scores[best_regime] / total) * 100))

    regime_info = next(r for r in REGIMES if r["id"] == best_regime)

    # Build explanation
    top_signals = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
    explanations = []
    for regime_id, score in top_signals:
        if score > 0:
            r = next(r for r in REGIMES if r["id"] == regime_id)
            explanations.append(f"{r['label']}: {r['description']}")

    explanation = ". ".join(explanations) + "." if explanations else "Insufficient data for regime classification."

    return {
        "current": regime_info["label"],
        "confidence": confidence,
        "since": datetime.now().isoformat(),
        "explanation": explanation,
        "scores": scores,
        "allRegimes": REGIMES,
    }


def update_regime():
    """Detect regime and update hub."""
    hub.regime = detect_regime()
