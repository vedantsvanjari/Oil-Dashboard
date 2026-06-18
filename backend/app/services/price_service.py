import logging
import threading
import yfinance as yf
from datetime import datetime, timezone, timedelta
from cachetools import TTLCache, cached
from sqlalchemy.orm import Session
from app.models.prices import Price

logger = logging.getLogger(__name__)

# Canonical symbol -> yfinance ticker map, shared across price helpers.
TICKERS_MAP = {
    "brent": "BZ=F",
    "wti": "CL=F",
    "gasoline": "RB=F",
    "heating_oil": "HO=F",
}

# TTL caches so rapid dashboard refreshes reuse recent results instead of firing
# redundant yfinance calls. Locks make them safe to read/write from FastAPI's
# threadpool (sync routes run concurrently in worker threads).
_LIVE_CACHE = TTLCache(maxsize=1, ttl=60)          # live snapshot: refresh at most once/min
_LIVE_LOCK = threading.Lock()
_HISTORY_CACHE = TTLCache(maxsize=16, ttl=900)     # 5y daily history: refresh every 15 min
_HISTORY_LOCK = threading.Lock()


def _fetch_live_external() -> dict:
    """Fetch latest close per instrument from yfinance (no DB, no caching)."""
    result = {}
    for key, ticker_symbol in TICKERS_MAP.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # 5d window avoids empty datasets on weekends/holidays.
            hist = ticker.history(period="5d")
            logger.debug("Live fetch %s: shape=%s empty=%s", ticker_symbol, hist.shape, hist.empty)

            if not hist.empty:
                result[key] = round(float(hist['Close'].iloc[-1]), 2)
            else:
                logger.warning("No live data returned for %s", ticker_symbol)
                result[key] = 0.0
        except Exception as e:
            logger.error("Live fetch failed for %s: %s", ticker_symbol, e)
            result[key] = 0.0

    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result


def _persist_live_prices(db: Session, result: dict) -> None:
    try:
        dt = datetime.fromisoformat(result["timestamp"])
        for key in ["brent", "wti", "gasoline", "heating_oil"]:
            if key in result:
                db.add(Price(symbol=key, price=result[key], timestamp=dt))
        db.commit()
    except Exception as e:
        logger.error("Error saving live prices to DB: %s", e)
        db.rollback()


def fetch_live_prices(db: Session = None):
    """Return latest live prices, cached for the TTL window. Persists only on a
    cache miss so repeated refreshes don't fire yfinance calls or write duplicate rows."""
    with _LIVE_LOCK:
        cached_result = _LIVE_CACHE.get("live")
        if cached_result is not None:
            return cached_result

        result = _fetch_live_external()
        if db:
            _persist_live_prices(db, result)
        _LIVE_CACHE["live"] = result
        return result


@cached(_HISTORY_CACHE, lock=_HISTORY_LOCK)
def fetch_historical_prices(symbol: str):
    if symbol not in TICKERS_MAP:
        return None

    ticker_symbol = TICKERS_MAP[symbol]

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
        logger.error("Error fetching historical data for %s: %s", symbol, e)
        return []


def fetch_intraday_prices(db: Session, period: str = "5d", interval: str = "15m") -> dict:
    """Fetch recent intraday bars from yfinance and persist new ones to the prices table.

    Designed to be called periodically by a background task. Existing bars (matched on
    symbol + timestamp) are skipped so repeated runs are idempotent. Returns a per-symbol
    count of newly inserted rows. This is a blocking (synchronous) function — callers in
    an async context should run it in a thread (e.g. asyncio.to_thread).
    """
    inserted = {}
    for symbol, ticker_symbol in TICKERS_MAP.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            hist = ticker.history(period=period, interval=interval)
            if hist.empty:
                inserted[symbol] = 0
                continue

            # Normalize bar timestamps to UTC-aware datetimes.
            index = hist.index
            if index.tz is not None:
                index = index.tz_convert("UTC")
            timestamps = [ts.to_pydatetime() for ts in index]

            # Load existing timestamps for this symbol in the fetched window to dedupe.
            window_start = min(timestamps)
            existing = {
                row[0]
                for row in db.query(Price.timestamp)
                .filter(Price.symbol == symbol, Price.timestamp >= window_start)
                .all()
            }

            count = 0
            for ts, (_, row) in zip(timestamps, hist.iterrows()):
                close = row.get("Close")
                if close is None or close != close:  # skip NaN
                    continue
                if ts in existing:
                    continue
                db.add(Price(symbol=symbol, price=round(float(close), 4), timestamp=ts))
                count += 1

            db.commit()
            inserted[symbol] = count
        except Exception as e:
            db.rollback()
            logger.error("Intraday ingestion failed for %s: %s", symbol, e)
            inserted[symbol] = 0

    logger.info("Intraday ingestion complete: %s", inserted)
    return inserted


def get_intraday_prices(db: Session, symbol: str, days: int = 5):
    """Return persisted intraday price points for a symbol over the last `days` days."""
    if symbol not in TICKERS_MAP:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(Price)
        .filter(Price.symbol == symbol, Price.timestamp >= cutoff)
        .order_by(Price.timestamp.asc())
        .all()
    )
    return [
        {"timestamp": r.timestamp.isoformat(), "close": round(float(r.price), 4)}
        for r in rows
    ]
