"""
Oil Trading Desk — Kalman Filter Analytics

Tracks the dynamic relationship between WTI and DXY using a 2-state Kalman Filter.
Estimates `alpha` (intercept) and `beta` (slope) for the equation:
    WTI_price = alpha + beta * DXY_price + error

Also calculates the current residual z-score.
"""

import numpy as np
import logging
from hub import hub

logger = logging.getLogger("otd.analytics.kalman")

# ── State Initialization ──────────────────────────────────────

# State vector: [alpha, beta]^T
state_mean = np.zeros(2)
# Covariance matrix of the state estimate
state_cov = np.eye(2)

# Transition matrix (Identity, assuming random walk of parameters)
transition_matrix = np.eye(2)

# Process noise covariance (controls how fast alpha and beta can drift)
# Tuned for daily/intraday commodity-fx drift
process_noise = np.array([
    [1e-4, 0],
    [0, 1e-4]
])

# Observation noise variance
observation_noise = 1.0

is_initialized = False


def initialize(wti_history: list, dxy_history: list):
    """
    Initialize the Kalman filter using historical data.
    Uses ordinary least squares (OLS) on the first batch of data.
    """
    global state_mean, state_cov, is_initialized

    if len(wti_history) < 20 or len(dxy_history) < 20:
        return

    # Align history (assume daily closes)
    # Simplified: just take the last N items
    min_len = min(len(wti_history), len(dxy_history))
    
    # We need prices for OLS
    try:
        y = np.array([d.get("close", 0) for d in wti_history[-min_len:]])
        x = np.array([d.get("close", 0) for d in dxy_history[-min_len:]])
        
        if len(y) < 20:
            return
            
        # OLS to find initial alpha and beta
        A = np.vstack([np.ones(len(x)), x]).T
        alpha, beta = np.linalg.lstsq(A, y, rcond=None)[0]
        
        state_mean = np.array([alpha, beta])
        state_cov = np.eye(2) * 1.0  # Initial uncertainty
        is_initialized = True
        
        logger.info(f"Kalman filter initialized: alpha={alpha:.4f}, beta={beta:.4f}")
    except Exception as e:
        logger.warning(f"Kalman initialization failed: {e}")


def update_kalman():
    """
    Run one iteration of the Kalman filter using the latest WTI and DXY prices.
    Writes the result to hub.kalman.
    """
    global state_mean, state_cov, is_initialized
    
    prices = hub.prices
    wti_data = prices.get("wti")
    
    if not wti_data or hub.dxy_value <= 0:
        return
        
    wti_price = wti_data.get("price", 0)
    dxy_price = hub.dxy_value
    
    if wti_price <= 0 or dxy_price <= 0:
        return

    # Check if we need to initialize
    if not is_initialized:
        # Try to initialize from history
        wti_hist = hub.price_history.get("wti", [])
        dxy_hist = hub.price_history.get("dxy", [])
        if wti_hist and dxy_hist:
            initialize(wti_hist, dxy_hist)
        else:
            return

    try:
        # ── Prediction Step ───────────────────────────────────────
        pred_state_mean = transition_matrix.dot(state_mean)
        pred_state_cov = transition_matrix.dot(state_cov).dot(transition_matrix.T) + process_noise

        # ── Observation Step ──────────────────────────────────────
        # Observation matrix H = [1, DXY]
        H = np.array([[1.0, dxy_price]])
        
        # Expected observation
        expected_wti = H.dot(pred_state_mean)[0]
        
        # Innovation (residual)
        residual = wti_price - expected_wti
        
        # Innovation covariance
        S = H.dot(pred_state_cov).dot(H.T) + observation_noise
        
        # Kalman gain
        K = pred_state_cov.dot(H.T).dot(np.linalg.inv(S))
        
        # ── Update Step ───────────────────────────────────────────
        state_mean = pred_state_mean + (K.dot(residual)).flatten()
        state_cov = (np.eye(2) - K.dot(H)).dot(pred_state_cov)
        
        # Calculate recent volatility for z-score
        # For simplicity, use the innovation standard deviation directly from S
        residual_std = np.sqrt(S[0, 0])
        z_score = residual / residual_std if residual_std > 0 else 0
        
        # Update hub
        hub.kalman = {
            "alpha": float(state_mean[0]),
            "beta": float(state_mean[1]),
            "expectedWti": float(expected_wti),
            "residual": float(residual),
            "zScore": float(z_score),
            "isOutlier": abs(z_score) > 2.0
        }
        
    except Exception as e:
        logger.error(f"Kalman update error: {e}")
