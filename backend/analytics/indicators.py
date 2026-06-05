"""
Oil Trading Desk — Technical Indicators

Computes EMA, Bollinger Bands, RSI, VWAP, and EWMA correlation matrix.
Applied to price history data from the hub.
"""

import logging
import math

import numpy as np

logger = logging.getLogger("otd.analytics.indicators")


def compute_ema(prices: list[float], period: int) -> list[float | None]:
    """
    Compute Exponential Moving Average.
    Returns list of same length, with None for positions before the EMA is ready.
    """
    if len(prices) < period:
        return [None] * len(prices)

    multiplier = 2 / (period + 1)
    ema = [None] * (period - 1)

    # Seed with SMA for the first value
    sma = sum(prices[:period]) / period
    ema.append(round(sma, 4))

    for i in range(period, len(prices)):
        val = (prices[i] - ema[-1]) * multiplier + ema[-1]
        ema.append(round(val, 4))

    return ema


def compute_bollinger(prices: list[float], period: int = 20, num_std: float = 2.0) -> list[dict | None]:
    """
    Compute Bollinger Bands (SMA ± num_std × σ).
    Returns list of {upper, middle, lower} or None.
    """
    results = []
    for i in range(len(prices)):
        if i < period - 1:
            results.append(None)
            continue

        window = prices[i - period + 1:i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        std_dev = math.sqrt(variance)

        results.append({
            "upper": round(mean + num_std * std_dev, 4),
            "middle": round(mean, 4),
            "lower": round(mean - num_std * std_dev, 4),
        })

    return results


def compute_rsi(prices: list[float], period: int = 14) -> list[float | None]:
    """
    Compute Relative Strength Index.
    """
    results = [None] * period
    for i in range(period, len(prices)):
        gains = 0.0
        losses = 0.0
        for j in range(i - period + 1, i + 1):
            diff = prices[j] - prices[j - 1]
            if diff > 0:
                gains += diff
            else:
                losses -= diff

        avg_gain = gains / period
        avg_loss = losses / period

        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        results.append(round(rsi, 1))

    return results


def compute_vwap(closes: list[float], volumes: list[int], period: int = 20) -> list[float | None]:
    """
    Compute Volume-Weighted Average Price (rolling approximation).
    """
    results = []
    for i in range(len(closes)):
        lookback = min(i + 1, period)
        start = max(0, i - lookback + 1)
        total_vol = sum(volumes[start:i + 1])
        if total_vol > 0:
            vwap = sum(
                closes[j] * volumes[j]
                for j in range(start, i + 1)
            ) / total_vol
            results.append(round(vwap, 4))
        else:
            results.append(round(closes[i], 4))

    return results


def apply_indicators(price_data: list[dict]) -> list[dict]:
    """
    Apply all indicators to a list of OHLCV records.
    Mutates each record in-place, adding ema20, ema50, vwap, bb*, rsi fields.
    Returns the same list for chaining.
    """
    closes = [d["close"] for d in price_data]
    volumes = [d.get("volume", 0) for d in price_data]

    ema20 = compute_ema(closes, 20)
    ema50 = compute_ema(closes, 50)
    bb = compute_bollinger(closes, 20)
    rsi = compute_rsi(closes, 14)
    vwap = compute_vwap(closes, volumes, 20)

    for i, d in enumerate(price_data):
        d["ema20"] = ema20[i]
        d["ema50"] = ema50[i]
        d["vwap"] = vwap[i] if i < len(vwap) else None

        if bb[i]:
            d["bbUpper"] = bb[i]["upper"]
            d["bbMiddle"] = bb[i]["middle"]
            d["bbLower"] = bb[i]["lower"]
        else:
            d["bbUpper"] = None
            d["bbMiddle"] = None
            d["bbLower"] = None

        d["rsi"] = rsi[i] if i < len(rsi) else None

    return price_data


def compute_ewma_correlation(returns_matrix: list[list[float]], lam: float = 0.94) -> list[list[float]]:
    """
    Compute EWMA correlation matrix (RiskMetrics λ=0.94).

    Args:
        returns_matrix: List of daily return series (one per asset).
                        Each inner list should be the same length.
        lam: Decay factor (default 0.94 for RiskMetrics).

    Returns:
        N×N correlation matrix as nested lists.
    """
    if not returns_matrix or not returns_matrix[0]:
        return []

    n = len(returns_matrix)
    T = len(returns_matrix[0])

    # Initialize covariance matrix with sample covariance
    arr = np.array(returns_matrix, dtype=np.float64)
    cov = np.cov(arr)

    # EWMA update
    for t in range(1, T):
        rt = arr[:, t].reshape(-1, 1)
        cov = lam * cov + (1 - lam) * (rt @ rt.T)

    # Convert to correlation
    std_devs = np.sqrt(np.diag(cov))
    std_devs[std_devs == 0] = 1.0  # Avoid division by zero
    corr = cov / np.outer(std_devs, std_devs)
    np.clip(corr, -1.0, 1.0, out=corr)

    return [[round(float(corr[i, j]), 2) for j in range(n)] for i in range(n)]


def compute_spread_stats(values: list[float], period: int = 20) -> dict:
    """
    Compute spread statistics: MA20, z-score, percentile.
    """
    if len(values) < period:
        return {"ma20": 0, "zScore": 0, "percentile": 50}

    recent = values[-period:]
    mean = sum(recent) / len(recent)
    variance = sum((x - mean) ** 2 for x in recent) / len(recent)
    std_dev = math.sqrt(variance) if variance > 0 else 1.0

    current = values[-1]
    z_score = (current - mean) / std_dev

    # Percentile rank within all values
    below = sum(1 for v in values if v < current)
    percentile = int((below / len(values)) * 100) if values else 50

    return {
        "ma20": round(mean, 3),
        "zScore": round(z_score, 2),
        "percentile": percentile,
    }
