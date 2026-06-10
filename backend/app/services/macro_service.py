import logging
from datetime import datetime
from sqlalchemy.orm import Session
import yfinance as yf
from app.models.macro import MacroData

logger = logging.getLogger(__name__)

def fetch_and_store_macro_data(db: Session, period: str = "1y"):
    """
    Fetches latest macro data from Yahoo Finance and stores it in PostgreSQL.
    Symbols used:
    DXY -> DX-Y.NYB
    US10Y -> ^TNX (10-Year Treasury Yield)
    US2Y -> ^IRX (13-Week Treasury Bill Yield, used as short-term proxy)
    """
    symbols = ["DX-Y.NYB", "^TNX", "^IRX"]
    
    try:
        # Download data using yfinance
        # period='1y' by default fetches approx 1 year of daily data
        data = yf.download(symbols, period=period, progress=False)
        
        # We need the 'Close' prices
        # yf.download returns a MultiIndex DataFrame if multiple symbols are passed
        if 'Close' not in data:
            logger.error("No 'Close' data returned from yfinance")
            return
            
        close_data = data['Close']
        
        # Iterate over the index (dates)
        for date_obj, row in close_data.iterrows():
            # Check for NaNs
            dxy_val = row['DX-Y.NYB'] if not bool(row.isna()['DX-Y.NYB']) else None
            us10y_val = row['^TNX'] if not bool(row.isna()['^TNX']) else None
            us2y_val = row['^IRX'] if not bool(row.isna()['^IRX']) else None
            
            # Do not process if critical metrics are missing
            if dxy_val is None or us10y_val is None:
                continue
            
            # Convert timestamp to date
            dt = date_obj.date()
            
            # Calculate Yield Curve
            yield_curve = None
            if us10y_val is not None and us2y_val is not None:
                yield_curve = round(float(us10y_val) - float(us2y_val), 4)
                
            record = db.query(MacroData).filter(MacroData.date == dt).first()
            if not record:
                record = MacroData(date=dt)
                db.add(record)
                
            if dxy_val is not None: record.dxy = float(dxy_val)
            if us10y_val is not None: record.us10y = float(us10y_val)
            if us2y_val is not None: record.us2y = float(us2y_val)
            if yield_curve is not None: record.yield_curve = yield_curve
            
        db.commit()
        
    except Exception as e:
        logger.error(f"Error fetching macro data from yfinance: {e}")

def get_latest_macro_data(db: Session):
    record = db.query(MacroData).filter(
        MacroData.dxy.isnot(None),
        MacroData.us10y.isnot(None)
    ).order_by(MacroData.date.desc()).first()
    if record:
        return {
            "date": record.date.isoformat(),
            "dxy": record.dxy,
            "us10y": record.us10y,
            "us2y": record.us2y,
            "yield_curve": record.yield_curve,
            "timestamp": record.date.isoformat() # Alias for frontend convenience
        }
    return None

def get_historical_macro_data(db: Session, limit: int = 260):
    records = db.query(MacroData).order_by(MacroData.date.desc()).limit(limit).all()
    return [
        {
            "date": r.date.isoformat(),
            "dxy": r.dxy,
            "us10y": r.us10y,
            "us2y": r.us2y,
            "yield_curve": r.yield_curve
        }
        for r in records
    ]
