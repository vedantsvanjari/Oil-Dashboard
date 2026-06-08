import yfinance as yf
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.prices import Price

def fetch_live_prices(db: Session = None):
    tickers_map = {
        "brent": "BZ=F",
        "wti": "CL=F",
        "gasoline": "RB=F",
        "heating_oil": "HO=F"
    }
    
    result = {}
    for key, ticker_symbol in tickers_map.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Using 5d based on your investigation to avoid empty datasets on weekends/holidays
            hist = ticker.history(period="5d")
            
            print(f"Ticker: {ticker_symbol}")
            print(f"hist.shape: {hist.shape}")
            print(f"hist.empty: {hist.empty}")
            
            if not hist.empty:
                latest_close = round(float(hist['Close'].iloc[-1]), 2)
                print(f"latest close price: {latest_close}")
                result[key] = latest_close
            else:
                print("latest close price: N/A")
                result[key] = 0.0
        except Exception as e:
            print(f"Ticker: {ticker_symbol}")
            print(f"Exception message: {str(e)}")
            result[key] = 0.0
            
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    if db:
        try:
            dt = datetime.fromisoformat(result["timestamp"])
            for key in ["brent", "wti", "gasoline", "heating_oil"]:
                if key in result:
                    new_price = Price(
                        symbol=key,
                        price=result[key],
                        timestamp=dt
                    )
                    db.add(new_price)
            db.commit()
        except Exception as e:
            print(f"Error saving to DB: {e}")
            db.rollback()

    return result

def fetch_historical_prices(symbol: str):
    tickers_map = {
        "brent": "BZ=F",
        "wti": "CL=F",
        "gasoline": "RB=F",
        "heating_oil": "HO=F"
    }
    
    if symbol not in tickers_map:
        return None
        
    ticker_symbol = tickers_map[symbol]
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="5y")
        
        result = []
        for date, row in hist.iterrows():
            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "close": round(float(row['Close']), 2)
            })
        return result
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        return []
