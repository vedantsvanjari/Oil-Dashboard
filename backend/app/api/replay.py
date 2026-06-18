from fastapi import APIRouter, HTTPException
import os
import json
from typing import Dict, Any, List

router = APIRouter()

def get_json_cache(filename: str):
    path = os.path.join(os.path.dirname(__file__), f"../models/ml/{filename}")
    if not os.path.exists(path):
        raise HTTPException(status_code=503, detail=f"{filename} cache not found. Run replay_engine.py first.")
    with open(path, 'r') as f:
        return json.load(f)

@router.get("/performance", summary="Get historical replay performance metrics")
def get_replay_performance() -> Dict[str, Any]:
    return get_json_cache("replay_performance.json")

@router.get("/trades", summary="Get historical replay trade logs")
def get_replay_trades() -> List[Dict[str, Any]]:
    return get_json_cache("replay_trades.json")
