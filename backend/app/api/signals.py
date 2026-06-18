from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.signal_engine import generate_current_signal
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _is_missing_table(exc: Exception) -> bool:
    """True when the exception indicates regime_targets does not exist."""
    text = str(getattr(exc, "orig", exc)).lower()
    return "regime_targets" in text or "no such table" in text or "does not exist" in text


@router.get("/current")
def get_current_signals() -> Dict[str, Any]:
    try:
        response = generate_current_signal()
        return response
    except FileNotFoundError as e:
        logger.error(f"Signal generation error: {e}")
        raise HTTPException(status_code=503, detail="Signal models not trained yet.")
    except ValueError as e:
        logger.error(f"Signal generation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # regime_targets is created by the offline pipeline; if it has not run yet the
        # query raises a DB error. Report it as "not run" instead of a generic 500.
        if _is_missing_table(e):
            return {"available": False, "message": "Data pipeline has not been run yet"}
        logger.error(f"Unexpected error in signal generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signal generation.")
