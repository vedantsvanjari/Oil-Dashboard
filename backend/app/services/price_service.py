import yfinance as yf
from datetime import datetime, timezone

def fetch_live_prices():
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
                latest_close = float(hist['Close'].iloc[-1])
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
    return result
