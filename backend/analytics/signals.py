"""
Oil Trading Desk — Sentiment Engine Signal Generation

Generates the 9 sentiment engine signals that feed the frontend's
composite sentiment score gauge. Each signal has a direction (BULL/BEAR/NEUT),
a score (0-100), a weight, and explanatory text.

Signals:
  1. Curve Structure     (weight 20)
  2. EIA Inventory       (weight 18)
  3. OPEC+ Compliance    (weight 15)
  4. USD / DXY           (weight 12)
  5. Crack Spreads       (weight 10)
  6. Geopolitical Risk   (weight 10)
  7. Rig Count Trend     (weight 8)
  8. Positioning (CFTC)  (weight 7)
  9. News Sentiment      (weight 10)
"""

import logging

from hub import hub
from feeds.sentiment import compute_aggregate_sentiment

logger = logging.getLogger("otd.analytics.signals")


def _curve_signal() -> dict:
    """Signal 1: Curve structure — backwardation vs contango."""
    spreads = hub.spreads
    m1m12 = next((s for s in spreads if s["id"] == "m1m12"), None) if spreads else None

    if not m1m12:
        return _default_signal("curveStructure", "Curve Structure", 20)

    value = m1m12["value"]
    z_score = m1m12.get("zScore", 0)

    if value > 2.0:
        signal, score = "BULL", min(95, 70 + int(value * 5))
        detail = f"M1-M12 at +${value:.2f} — strong physical tightness"
    elif value > 0.5:
        signal, score = "BULL", 60 + int(value * 10)
        detail = f"M1-M12 at +${value:.2f} — moderate backwardation"
    elif value > 0:
        signal, score = "NEUT", 50 + int(value * 20)
        detail = f"M1-M12 at +${value:.2f} — slight backwardation"
    elif value > -1.0:
        signal, score = "BEAR", 40 + int(value * 10)
        detail = f"M1-M12 at ${value:.2f} — mild contango"
    else:
        signal, score = "BEAR", max(10, 30 + int(value * 5))
        detail = f"M1-M12 at ${value:.2f} — deep contango, oversupply signal"

    return {
        "storeKey": "curveStructure",
        "name": "Curve Structure",
        "value": f"{'Backwardation' if value > 0 else 'Contango'}",
        "detail": detail,
        "signal": signal,
        "weight": 20,
        "score": max(5, min(95, score)),
        "bullishReason": "Strong backwardation signals physical tightness and near-term supply deficit.",
        "bearishReason": "If contango develops, it signals oversupply and incentivizes storage builds.",
        "marketImpact": "Backwardation discourages floating storage and accelerates physical drawdowns.",
    }


def _eia_signal() -> dict:
    """Signal 2: EIA inventory draws/builds."""
    fundamentals = hub.fundamentals
    crude = fundamentals.get("crude_stocks", {})

    if not crude:
        return _default_signal("eiaInventory", "EIA Inventory", 18)

    change = crude.get("weekChange", 0)

    if change < -2.0:
        signal, score = "BULL", 80
        detail = f"{change:+.1f} mn bbl — large draw, physical demand outpacing supply"
    elif change < 0:
        signal, score = "BULL", 65
        detail = f"{change:+.1f} mn bbl — draw week"
    elif change < 2.0:
        signal, score = "NEUT", 45
        detail = f"{change:+.1f} mn bbl — modest build"
    else:
        signal, score = "BEAR", 30
        detail = f"{change:+.1f} mn bbl — large build, bearish for spot"

    return {
        "storeKey": "eiaInventory",
        "name": "EIA Inventory",
        "value": f"{change:+.1f} mn bbl",
        "detail": detail,
        "signal": signal,
        "weight": 18,
        "score": score,
        "bullishReason": "Consecutive draws indicate demand outpacing supply.",
        "bearishReason": "If draws reverse to builds, it signals weakening demand.",
        "marketImpact": "Cushing hub draws are particularly significant — directly support WTI pricing.",
    }


def _opec_signal() -> dict:
    """Signal 3: OPEC+ compliance."""
    opec = hub.opec

    if not opec:
        return _default_signal("opecCompliance", "OPEC+ Compliance", 15)

    compliance = opec.get("compliancePercent", 0)

    if compliance >= 99:
        signal, score = "BULL", 85
        detail = f"{compliance:.1f}% — near-full compliance, cuts effective"
    elif compliance >= 95:
        signal, score = "BULL", 70
        detail = f"{compliance:.1f}% — high compliance"
    elif compliance >= 90:
        signal, score = "NEUT", 55
        detail = f"{compliance:.1f}% — moderate compliance, some cheating"
    else:
        signal, score = "BEAR", 35
        detail = f"{compliance:.1f}% — low compliance, cuts eroding"

    return {
        "storeKey": "opecCompliance",
        "name": "OPEC+ Compliance",
        "value": f"{compliance:.1f}%",
        "detail": detail,
        "signal": signal,
        "weight": 15,
        "score": score,
        "bullishReason": "High compliance means supply discipline is holding.",
        "bearishReason": "If cheating accelerates, effective cuts diminish.",
        "marketImpact": "OPEC+ credibility directly influences speculative positioning.",
    }


def _dxy_signal() -> dict:
    """Signal 4: USD / DXY."""
    dxy = hub.dxy_value
    change = hub.dxy_change

    if dxy <= 0:
        return _default_signal("usdDxy", "USD / DXY", 12)

    if change < -0.3:
        signal, score = "BULL", 75
        detail = f"DXY {dxy:.2f} ({change:+.2f}) — falling dollar supports crude"
    elif change < 0:
        signal, score = "BULL", 60
        detail = f"DXY {dxy:.2f} ({change:+.2f}) — mild dollar weakness"
    elif change < 0.3:
        signal, score = "NEUT", 50
        detail = f"DXY {dxy:.2f} ({change:+.2f}) — stable dollar"
    else:
        signal, score = "BEAR", 35
        detail = f"DXY {dxy:.2f} ({change:+.2f}) — rising dollar headwind"

    return {
        "storeKey": "usdDxy",
        "name": "USD / DXY",
        "value": f"{dxy:.2f} ({change:+.2f})",
        "detail": detail,
        "signal": signal,
        "weight": 12,
        "score": score,
        "bullishReason": "Weakening dollar makes oil cheaper for non-USD buyers.",
        "bearishReason": "A strengthening dollar compresses commodity prices.",
        "marketImpact": f"DXY at {dxy:.2f} — the dollar is a significant macro driver.",
    }


def _crack_signal() -> dict:
    """Signal 5: Crack spreads."""
    crack = hub.crack_spread

    if not crack:
        return _default_signal("crackSpreads", "Crack Spreads", 10)

    value = crack.get("value", 0)

    if value > 25:
        signal, score = "BULL", 90
        detail = f"${value:.2f}/bbl — exceptional refining margins"
    elif value > 15:
        signal, score = "BULL", 68
        detail = f"${value:.2f}/bbl — healthy refining margins"
    elif value > 10:
        signal, score = "NEUT", 50
        detail = f"${value:.2f}/bbl — average margins"
    else:
        signal, score = "BEAR", 30
        detail = f"${value:.2f}/bbl — weak margins, demand concern"

    return {
        "storeKey": "crackSpreads",
        "name": "Crack Spreads",
        "value": f"${value:.2f}/bbl",
        "detail": detail,
        "signal": signal,
        "weight": 10,
        "score": score,
        "bullishReason": "Strong cracks incentivize refiners to run at high utilization.",
        "bearishReason": "Crack compression signals product oversupply.",
        "marketImpact": f"Current 3:2:1 at ${value:.2f} — {'exceptional' if value > 25 else 'normal' if value > 10 else 'weak'} range.",
    }


def _geo_signal() -> dict:
    """Signal 6: Geopolitical risk (from news flow)."""
    news = list(hub.news)
    recent = news[:30]  # Last 30 items

    geo_count = sum(1 for n in recent if n.get("category") == "Geopolitics")
    geo_pct = (geo_count / max(len(recent), 1)) * 100

    if geo_pct > 30:
        signal, score = "BULL", 80
        detail = f"{geo_count} geopolitical headlines in last {len(recent)} — elevated risk premium"
    elif geo_pct > 15:
        signal, score = "BULL", 65
        detail = f"{geo_count} geopolitical headlines — moderate risk"
    elif geo_pct > 5:
        signal, score = "NEUT", 50
        detail = "Normal geopolitical noise"
    else:
        signal, score = "NEUT", 45
        detail = "Low geopolitical activity"

    return {
        "storeKey": "geopoliticalRisk",
        "name": "Geopolitical Risk",
        "value": "Elevated" if score > 60 else "Normal" if score > 40 else "Low",
        "detail": detail,
        "signal": signal,
        "weight": 10,
        "score": score,
        "bullishReason": "Supply disruptions add risk premium to crude.",
        "bearishReason": "Geopolitical premiums evaporate on de-escalation.",
        "marketImpact": "Supply-side geopolitical risk is most impactful in tight physical markets.",
    }


def _rig_signal() -> dict:
    """Signal 7: Rig count trend."""
    fundamentals = hub.fundamentals
    rig = fundamentals.get("rig_count", {})

    if not rig:
        return _default_signal("rigCount", "Rig Count Trend", 8)

    value = rig.get("value", 0)
    change = rig.get("weekChange", 0)

    if change < -5:
        signal, score = "BULL", 75
        detail = f"{value} rigs ({change:+d} WoW) — significant decline, less future supply"
    elif change < 0:
        signal, score = "BULL", 62
        detail = f"{value} rigs ({change:+d} WoW) — declining, supports future prices"
    elif change == 0:
        signal, score = "NEUT", 50
        detail = f"{value} rigs — unchanged"
    else:
        signal, score = "BEAR", 40
        detail = f"{value} rigs ({change:+d} WoW) — rising, bearish for future supply"

    return {
        "storeKey": "rigCount",
        "name": "Rig Count Trend",
        "value": f"{int(value)} ({change:+d} WoW)",
        "detail": detail,
        "signal": signal,
        "weight": 8,
        "score": score,
        "bullishReason": "Declining rig count means US shale production growth is decelerating.",
        "bearishReason": "Shale productivity gains can offset rig declines.",
        "marketImpact": "Medium-term signal: rig count changes take 4-6 months to flow to production.",
    }


def _cot_signal() -> dict:
    """Signal 8: CFTC COT positioning."""
    cot = hub.cot

    if not cot:
        return _default_signal("positioning", "Positioning (CFTC)", 7)

    mm = cot.get("managed_money", {})
    net = mm.get("net", 0)
    net_change = mm.get("net_change", 0)

    if net_change > 20000:
        signal, score = "BULL", 78
        detail = f"Net Long +{net_change:,d} — aggressive speculative buying"
    elif net_change > 0:
        signal, score = "BULL", 65
        detail = f"Net Long +{net_change:,d} — specs adding length"
    elif net_change > -10000:
        signal, score = "NEUT", 50
        detail = f"Net change {net_change:+,d} — minimal repositioning"
    else:
        signal, score = "BEAR", 35
        detail = f"Net change {net_change:+,d} — specs reducing exposure"

    return {
        "storeKey": "positioning",
        "name": "Positioning (CFTC)",
        "value": f"Net {'+' if net_change >= 0 else ''}{net_change // 1000}K",
        "detail": detail,
        "signal": signal,
        "weight": 7,
        "score": score,
        "bullishReason": "Hedge funds adding net longs signals bullish conviction.",
        "bearishReason": "Extreme net long positioning increases liquidation risk.",
        "marketImpact": "Current positioning context affects vulnerability to short squeezes or long liquidation.",
    }


def _news_sentiment_signal() -> dict:
    """Signal 9: Aggregate news sentiment."""
    news = list(hub.news)

    if not news:
        return _default_signal("newsSentiment", "News Sentiment", 10)

    sentiments = [{"compound": n.get("sentimentScore", 0), "signal": n.get("sentiment", "neutral")} for n in news[:30]]
    agg = compute_aggregate_sentiment(sentiments)

    bullish = agg["bullish_count"]
    bearish = agg["bearish_count"]
    total = bullish + bearish + agg["neutral_count"]

    if agg["avg_compound"] > 0.15:
        signal, score = "BULL", 73
    elif agg["avg_compound"] > 0.05:
        signal, score = "BULL", 60
    elif agg["avg_compound"] > -0.05:
        signal, score = "NEUT", 50
    elif agg["avg_compound"] > -0.15:
        signal, score = "BEAR", 40
    else:
        signal, score = "BEAR", 25

    return {
        "storeKey": "newsSentiment",
        "name": "News Sentiment",
        "value": f"{bullish} Bull / {bearish} Bear",
        "detail": f"{int(bullish / max(total, 1) * 100)}% of headlines carry bullish sentiment ({total} items)",
        "signal": signal,
        "weight": 10,
        "score": score,
        "bullishReason": "Overwhelmingly bullish news flow reinforces the current trend.",
        "bearishReason": "Bearish narratives gaining traction can shift sentiment.",
        "marketImpact": "News sentiment acts as a sentiment amplifier — aligned headlines sustain moves.",
    }


def _default_signal(key: str, name: str, weight: int) -> dict:
    """Default signal when data is unavailable."""
    return {
        "storeKey": key,
        "name": name,
        "value": "N/A",
        "detail": "Data not yet available",
        "signal": "NEUT",
        "weight": weight,
        "score": 50,
        "bullishReason": "—",
        "bearishReason": "—",
        "marketImpact": "—",
    }


def generate_signals() -> dict:
    """
    Generate all 9 sentiment engine signals and compute the aggregate score.
    Returns a dict matching the frontend's sentimentAnalysis shape.
    """
    signals = [
        _curve_signal(),
        _eia_signal(),
        _opec_signal(),
        _dxy_signal(),
        _crack_signal(),
        _geo_signal(),
        _rig_signal(),
        _cot_signal(),
        _news_sentiment_signal(),
    ]

    # Compute weighted average score
    total_weight = sum(s["weight"] for s in signals)
    weighted_score = sum(s["score"] * s["weight"] for s in signals) / max(total_weight, 1)
    score = int(weighted_score)

    if score >= 75:
        overall = "STRONGLY BULLISH"
    elif score >= 62:
        overall = "BULLISH"
    elif score >= 55:
        overall = "SLIGHTLY BULLISH"
    elif score >= 45:
        overall = "NEUTRAL"
    elif score >= 38:
        overall = "SLIGHTLY BEARISH"
    elif score >= 25:
        overall = "BEARISH"
    else:
        overall = "STRONGLY BEARISH"

    # Generate risk/catalyst lists from active signals
    risks = []
    catalysts = []
    for s in signals:
        if s["signal"] == "BEAR" and s["bearishReason"] != "—":
            risks.append(s["bearishReason"])
        if s["signal"] == "BULL" and s["bullishReason"] != "—":
            catalysts.append(s["bullishReason"])

    return {
        "overall": overall,
        "score": score,
        "priceDirection": "Higher prices likely" if score >= 55 else "Range-bound" if score >= 45 else "Lower prices likely",
        "summary": f"Composite sentiment score: {score}/100 based on {len(signals)} fundamental signals.",
        "signals": signals,
        "risks": risks[:5],
        "catalysts": catalysts[:5],
    }


def update_signals():
    """Generate signals and update hub."""
    hub.sentiment = generate_signals()
