"""
Oil Trading Desk — VADER Sentiment Analysis with Oil Finance Lexicon

Scores news headlines using VADER with a custom oil/commodity
lexicon overlay to improve domain-specific accuracy.

Thresholds:
  compound >= +0.15 → BULLISH
  compound <= -0.15 → BEARISH
  else               → NEUTRAL
"""

import logging

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger("otd.feeds.sentiment")

# ── Custom oil finance lexicon overlay ────────────────────────
# These augment VADER's default lexicon with domain-specific terms.
# Positive values = bullish, negative = bearish.
OIL_FINANCE_LEXICON = {
    # Supply-side bullish
    "backwardation": 0.3,
    "draw": 0.4,
    "draws": 0.4,
    "drawdown": 0.4,
    "tightening": 0.3,
    "tightness": 0.3,
    "cut": 0.2,
    "cuts": 0.2,
    "curtailment": 0.3,
    "disruption": 0.3,
    "disruptions": 0.3,
    "outage": 0.3,
    "outages": 0.3,
    "sanctions": 0.2,
    "embargo": 0.3,
    "shortage": 0.4,
    "deficit": 0.3,
    "squeeze": 0.3,
    "rally": 0.4,
    "rallies": 0.4,
    "surge": 0.3,
    "surges": 0.3,
    "compliance": 0.2,

    # Demand-side bullish
    "demand": 0.1,
    "recovery": 0.2,
    "rebound": 0.2,
    "growth": 0.2,

    # Supply-side bearish
    "contango": -0.3,
    "build": -0.3,
    "builds": -0.3,
    "surplus": -0.4,
    "oversupply": -0.4,
    "oversupplied": -0.4,
    "glut": -0.5,
    "overproduction": -0.3,
    "ramp": -0.2,
    "flooding": -0.3,
    "flood": -0.3,

    # Demand-side bearish
    "recession": -0.4,
    "slowdown": -0.3,
    "destruction": -0.3,
    "weakness": -0.3,
    "weak": -0.2,
    "decline": -0.3,
    "declining": -0.3,
    "crash": -0.5,
    "plunge": -0.4,
    "plunges": -0.4,
    "tumble": -0.3,
    "slump": -0.3,

    # Geopolitical
    "war": 0.2,
    "conflict": 0.2,
    "attack": 0.2,
    "attacks": 0.2,
    "houthi": 0.2,
    "missile": 0.2,
    "military": 0.1,
    "ceasefire": -0.2,
    "peace": -0.2,
    "deal": -0.1,
    "diplomacy": -0.1,

    # OPEC-specific
    "opec": 0.0,  # Neutral — context matters
    "opec+": 0.0,
    "quota": 0.1,
    "production target": 0.1,
}

# Threshold for signal classification
BULLISH_THRESHOLD = 0.15
BEARISH_THRESHOLD = -0.15

# ── Analyzer singleton ───────────────────────────────────────
_analyzer = None


def _get_analyzer() -> SentimentIntensityAnalyzer:
    """Lazy-init VADER analyzer with custom oil finance lexicon."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentIntensityAnalyzer()
        _analyzer.lexicon.update(OIL_FINANCE_LEXICON)
        logger.info(f"VADER initialized with {len(OIL_FINANCE_LEXICON)} custom oil finance terms")
    return _analyzer


def score_headline(headline: str) -> dict:
    """
    Score a single headline and return sentiment data.

    Returns:
        {
            "compound": float,     # -1.0 to +1.0
            "positive": float,     # 0.0 to 1.0
            "negative": float,     # 0.0 to 1.0
            "neutral": float,      # 0.0 to 1.0
            "signal": str,         # "bullish" | "bearish" | "neutral"
        }
    """
    analyzer = _get_analyzer()
    scores = analyzer.polarity_scores(headline)

    compound = scores["compound"]
    if compound >= BULLISH_THRESHOLD:
        signal = "bullish"
    elif compound <= BEARISH_THRESHOLD:
        signal = "bearish"
    else:
        signal = "neutral"

    return {
        "compound": round(compound, 4),
        "positive": round(scores["pos"], 4),
        "negative": round(scores["neg"], 4),
        "neutral": round(scores["neu"], 4),
        "signal": signal,
    }


def score_headlines_batch(headlines: list[str]) -> list[dict]:
    """Score multiple headlines at once."""
    return [score_headline(h) for h in headlines]


def compute_aggregate_sentiment(sentiments: list[dict]) -> dict:
    """
    Compute aggregate sentiment across a batch of scored items.

    Returns:
        {
            "bullish_count": int,
            "bearish_count": int,
            "neutral_count": int,
            "avg_compound": float,
            "overall_signal": str,
        }
    """
    if not sentiments:
        return {
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "avg_compound": 0.0,
            "overall_signal": "neutral",
        }

    bullish = sum(1 for s in sentiments if s["signal"] == "bullish")
    bearish = sum(1 for s in sentiments if s["signal"] == "bearish")
    neutral = sum(1 for s in sentiments if s["signal"] == "neutral")
    avg = sum(s["compound"] for s in sentiments) / len(sentiments)

    if avg >= BULLISH_THRESHOLD:
        overall = "bullish"
    elif avg <= BEARISH_THRESHOLD:
        overall = "bearish"
    else:
        overall = "neutral"

    return {
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "avg_compound": round(avg, 4),
        "overall_signal": overall,
    }
