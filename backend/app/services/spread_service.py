import logging
from datetime import timedelta
from sqlalchemy.orm import Session
from app.models.prices import Price

logger = logging.getLogger(__name__)

def get_brent_wti_spread(db: Session):
    """
    Calculates the Brent-WTI spread using historical price data stored in the DB.
    Matches each Brent record with the closest WTI record within a tolerance window.
    """
    brent_prices = db.query(Price).filter(Price.symbol == "brent").order_by(Price.timestamp.asc()).all()
    wti_prices = db.query(Price).filter(Price.symbol == "wti").order_by(Price.timestamp.asc()).all()
    
    logger.info(f"Number of Brent records found: {len(brent_prices)}")
    logger.info(f"Number of WTI records found: {len(wti_prices)}")
    
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
            
    logger.info(f"Number of matched pairs used: {matched_pairs}")
    logger.info(f"Number of spread history points returned: {len(history)}")
            
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
