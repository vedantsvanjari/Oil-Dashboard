from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.signal_engine import generate_current_signal
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

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
        logger.error(f"Unexpected error in signal generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during signal generation.")
