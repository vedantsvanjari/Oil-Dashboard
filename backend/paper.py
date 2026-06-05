"""
Oil Trading Desk — Paper Trading Logic

Manages a virtual paper trading book tracking P&L, positions, cash balance, and equity curve.
Performs mark-to-market (MTM) calculations based on current live prices.
"""

import logging
import time
from hub import hub

logger = logging.getLogger("otd.paper")

# Initial starting capital for the paper book
INITIAL_CASH = 1000000.0


def initialize_paper_book():
    """Set up the initial empty paper book state in the hub if not loaded from persistence."""
    if not hub.paper:
        hub.paper = {
            "cash": INITIAL_CASH,
            "positions": {},       # e.g., {"wti": {"qty": 1000, "avg_price": 75.0, "pnl": 0.0}}
            "equity": INITIAL_CASH,
            "equity_curve": [{"time": time.time(), "value": INITIAL_CASH}],
            "realized_pnl": 0.0,
            "last_mtm_time": time.time()
        }


def mark_to_market():
    """
    Update the paper book equity based on live market prices.
    Called periodically to compute unrealized P&L.
    """
    if not hub.paper:
        initialize_paper_book()
        
    paper = hub.paper
    unrealized_pnl = 0.0
    
    for symbol, pos in paper["positions"].items():
        price_data = hub.prices.get(symbol)
        if not price_data:
            continue
            
        current_price = price_data.get("price", 0.0)
        if current_price <= 0:
            continue
            
        qty = pos["qty"]
        avg_price = pos["avg_price"]
        
        # Calculate P&L
        pos_pnl = (current_price - avg_price) * qty
        pos["pnl"] = pos_pnl
        unrealized_pnl += pos_pnl
        
    paper["equity"] = paper["cash"] + unrealized_pnl
    
    # Record equity curve point every 5 minutes
    now = time.time()
    if now - paper["last_mtm_time"] >= 300:
        paper["equity_curve"].append({
            "time": now,
            "value": paper["equity"]
        })
        # Keep only last 288 points (24 hours at 5-min intervals)
        if len(paper["equity_curve"]) > 288:
            paper["equity_curve"].pop(0)
            
        paper["last_mtm_time"] = now


def execute_trade(symbol: str, qty: float, is_buy: bool):
    """
    Execute a virtual trade.
    Positive qty for buy, negative for sell.
    """
    if not hub.paper:
        initialize_paper_book()
        
    price_data = hub.prices.get(symbol)
    if not price_data:
        logger.warning(f"Cannot execute trade: No price for {symbol}")
        return False
        
    price = price_data.get("price", 0.0)
    if price <= 0:
        logger.warning(f"Cannot execute trade: Invalid price {price} for {symbol}")
        return False
        
    paper = hub.paper
    actual_qty = qty if is_buy else -qty
    trade_value = abs(actual_qty) * price
    
    if is_buy and paper["cash"] < trade_value:
        logger.warning(f"Insufficient cash for buy: Need {trade_value}, have {paper['cash']}")
        return False
        
    # Get or create position
    if symbol not in paper["positions"]:
        paper["positions"][symbol] = {"qty": 0.0, "avg_price": 0.0, "pnl": 0.0}
        
    pos = paper["positions"][symbol]
    
    # Simple average price math (ignoring short selling complexities for now)
    new_qty = pos["qty"] + actual_qty
    
    if new_qty == 0:
        # Position closed
        realized = pos["pnl"] + (price - pos["avg_price"]) * actual_qty if pos["qty"] > 0 else (pos["avg_price"] - price) * abs(actual_qty)
        paper["realized_pnl"] += realized
        paper["cash"] += (pos["qty"] * pos["avg_price"]) + realized
        del paper["positions"][symbol]
    else:
        # Position opened or added to
        if pos["qty"] == 0 or (pos["qty"] > 0 and actual_qty > 0) or (pos["qty"] < 0 and actual_qty < 0):
            # Adding to position: calculate new avg price
            pos["avg_price"] = ((pos["qty"] * pos["avg_price"]) + (actual_qty * price)) / new_qty
        else:
            # Partially reducing position: avg price stays same, realize some P&L
            closed_qty = abs(actual_qty)
            realized = (price - pos["avg_price"]) * actual_qty if pos["qty"] > 0 else (pos["avg_price"] - price) * abs(actual_qty)
            paper["realized_pnl"] += realized
            
        pos["qty"] = new_qty
        paper["cash"] -= actual_qty * price
        
    logger.info(f"TRADE EXECUTED: {'BUY' if is_buy else 'SELL'} {abs(actual_qty)} {symbol} @ {price}")
    mark_to_market()
    
    # In a real system, trigger persistence here
    return True
