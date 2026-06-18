import logging
import threading
from datetime import timedelta
from cachetools import TTLCache
from sqlalchemy.orm import Session
from app.models.prices import Price

logger = logging.getLogger(__name__)

# The spread is recomputed from the full price history with an O(n) two-pointer pass.
# Cache the result briefly so rapid dashboard refreshes reuse it instead of
# re-querying + recomputing every request.
_SPREAD_CACHE = TTLCache(maxsize=1, ttl=120)       # 2 min
_SPREAD_LOCK = threading.Lock()


def get_brent_wti_spread(db: Session):
    """
    Calculates the Brent-WTI spread using historical price data stored in the DB.
    Matches each Brent record with the closest WTI record within a tolerance window.
    Result is cached for a short TTL (see _SPREAD_CACHE).
    """
    with _SPREAD_LOCK:
        cached_result = _SPREAD_CACHE.get("brent-wti")
        if cached_result is not None:
            return cached_result
        result = _compute_brent_wti_spread(db)
        _SPREAD_CACHE["brent-wti"] = result
        return result


def _compute_brent_wti_spread(db: Session):
    brent_prices = db.query(Price).filter(Price.symbol == "brent").order_by(Price.timestamp.asc()).all()
    wti_prices = db.query(Price).filter(Price.symbol == "wti").order_by(Price.timestamp.asc()).all()

    logger.debug("Brent records: %s, WTI records: %s", len(brent_prices), len(wti_prices))

    history = []
    tolerance = timedelta(days=2) # 48 hours tolerance
    
    matched_pairs = 0
    wti_idx = 0
    num_wti = len(wti_prices)
    
    # Since both lists are sorted by timestamp ascending, we can use a two-pointer approach
    for bp in brent_prices:
        if num_wti == 0:
            break
            
        # Advance wti_idx until the next WTI price is further away from bp than the current one
        while wti_idx < num_wti - 1:
            curr_diff = abs(bp.timestamp - wti_prices[wti_idx].timestamp)
            next_diff = abs(bp.timestamp - wti_prices[wti_idx + 1].timestamp)
            if next_diff <= curr_diff:
                wti_idx += 1
            else:
                break
                
        best_wp = wti_prices[wti_idx]
        if abs(best_wp.timestamp - bp.timestamp) <= tolerance:
            spread = round(bp.price - best_wp.price, 2)
            history.append({
                "timestamp": bp.timestamp.isoformat(),
                "brent": bp.price,
                "wti": best_wp.price,
                "spread": spread
            })
            matched_pairs += 1
            
    logger.debug("Matched pairs: %s, spread history points: %s", matched_pairs, len(history))

    # Sort history descending to find latest easily
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    
    if not history:
        return {
            "current_spread": 0.0,
            "previous_spread": 0.0,
            "daily_change": 0.0,
            "history": []
        }
        
    current_spread = history[0]["spread"]
    previous_spread = history[1]["spread"] if len(history) > 1 else current_spread
    daily_change = round(current_spread - previous_spread, 2)
    
    return {
        "current_spread": current_spread,
        "previous_spread": previous_spread,
        "daily_change": daily_change,
        "history": history
    }
