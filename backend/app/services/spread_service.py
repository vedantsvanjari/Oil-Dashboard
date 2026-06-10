from sqlalchemy.orm import Session
from app.models.prices import Price

def get_brent_wti_spread(db: Session):
    """
    Calculates the Brent-WTI spread using historical price data stored in the DB.
    """
    brent_prices = db.query(Price).filter(Price.symbol == "brent").order_by(Price.timestamp.asc()).all()
    wti_prices = db.query(Price).filter(Price.symbol == "wti").order_by(Price.timestamp.asc()).all()
    
    # Map WTI prices by timestamp
    wti_dict = {p.timestamp: p.price for p in wti_prices}
    
    history = []
    for bp in brent_prices:
        wp = wti_dict.get(bp.timestamp)
        if wp is not None:
            spread = round(bp.price - wp, 2)
            history.append({
                "timestamp": bp.timestamp.isoformat(),
                "brent": bp.price,
                "wti": wp,
                "spread": spread
            })
            
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
