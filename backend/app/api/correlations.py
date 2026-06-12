"""
Correlations API Router
========================
Exposes heatmap-ready Pearson correlation matrices and top-N relationship endpoints.

Routes:
  GET /api/correlations/matrix         ?window=30D&matrix_type=product
  GET /api/correlations/top-positive   ?window=30D&n=10
  GET /api/correlations/top-negative   ?window=30D&n=10
  GET /api/correlations/datasets       List all auto-discovered datasets
  POST /api/correlations/refresh       Force-recompute all matrix types
"""
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.correlation_service import (
    discover_datasets,
    get_matrix,
    get_frontend_matrix,
    get_top_correlations,
    VALID_WINDOWS,
    MATRIX_GROUPS,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/datasets", summary="List all discoverable datasets")
def list_datasets(db: Session = Depends(get_db)):
    """
    Auto-discover every available dataset by introspecting all DB tables.
    Returns categorized list: energy, macro, fundamentals, spreads.
    """
    datasets = discover_datasets(db)
    by_category: dict = {}
    for d in datasets:
        cat = d["category"]
        by_category.setdefault(cat, []).append(d)

    return {
        "total": len(datasets),
        "categories": by_category,
    }


@router.get("/product", summary="Frontend Product Correlation Heatmap")
def get_product_heatmap(
    window: str = Query("30D", description="Time window: 7D, 30D, 90D, 180D"),
    force_refresh: bool = Query(False, description="Skip cache and recompute"),
    db: Session = Depends(get_db),
):
    if window not in VALID_WINDOWS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window '{window}'. Valid options: {list(VALID_WINDOWS.keys())}",
        )
    try:
        return get_frontend_matrix(db, window=window, matrix_type="product", force_refresh=force_refresh)
    except Exception as exc:
        logger.error("Error computing product heatmap: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error computing product heatmap")


@router.get("/spreads", summary="Frontend Spread Correlation Heatmap")
def get_spreads_heatmap(
    window: str = Query("30D", description="Time window: 7D, 30D, 90D, 180D"),
    force_refresh: bool = Query(False, description="Skip cache and recompute"),
    db: Session = Depends(get_db),
):
    if window not in VALID_WINDOWS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window '{window}'. Valid options: {list(VALID_WINDOWS.keys())}",
        )
    try:
        return get_frontend_matrix(db, window=window, matrix_type="spreads", force_refresh=force_refresh)
    except Exception as exc:
        logger.error("Error computing spread heatmap: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error computing spread heatmap")


@router.get("/macro", summary="Frontend Macro Correlation Heatmap")
def get_macro_heatmap(
    window: str = Query("30D", description="Time window: 7D, 30D, 90D, 180D"),
    force_refresh: bool = Query(False, description="Skip cache and recompute"),
    db: Session = Depends(get_db),
):
    if window not in VALID_WINDOWS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window '{window}'. Valid options: {list(VALID_WINDOWS.keys())}",
        )
    try:
        return get_frontend_matrix(db, window=window, matrix_type="macro", force_refresh=force_refresh)
    except Exception as exc:
        logger.error("Error computing macro heatmap: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error computing macro heatmap")


@router.get("/matrix", summary="Heatmap-ready correlation matrix")
def get_correlation_matrix(
    window: str = Query("30D", description="Time window: 7D, 30D, 90D, 180D"),
    matrix_type: str = Query(
        "product",
        description="Matrix group: product, spread, macro, inventory",
    ),
    force_refresh: bool = Query(False, description="Skip cache and recompute"),
    db: Session = Depends(get_db),
):
    """
    Return a Pearson correlation matrix ready for frontend heatmap rendering.

    Response format:
    ```json
    {
      "window": "30D",
      "matrix_type": "product",
      "labels": ["brent", "wti", "gasoline", "heating_oil", "dxy"],
      "matrix": [[1.0, 0.98, ...], ...],
      "computed_at": "...",
      "cached": true
    }
    ```

    The matrix is a square N×N array where `matrix[i][j]` is the Pearson
    correlation between `labels[i]` and `labels[j]`.
    Cached for 1 hour; use `force_refresh=true` to recompute immediately.
    """
    if window not in VALID_WINDOWS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window '{window}'. Valid options: {list(VALID_WINDOWS.keys())}",
        )
    if matrix_type not in MATRIX_GROUPS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid matrix_type '{matrix_type}'. Valid options: {list(MATRIX_GROUPS.keys())}",
        )

    try:
        result = get_matrix(db, window=window, matrix_type=matrix_type, force_refresh=force_refresh)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error computing correlation matrix: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error computing correlation matrix")


@router.get("/top-positive", summary="Top N strongest positive correlations")
def get_top_positive(
    window: str = Query("30D", description="Time window: 7D, 30D, 90D, 180D"),
    n: int = Query(10, ge=1, le=50, description="Number of pairs to return"),
    db: Session = Depends(get_db),
):
    """
    Return the N asset pairs with the highest positive Pearson correlation
    across all datasets (energy, macro, fundamentals, spreads).

    Response format:
    ```json
    [
      {"asset_1": "wti", "asset_2": "brent", "correlation": 0.98},
      ...
    ]
    ```
    """
    if window not in VALID_WINDOWS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window '{window}'. Valid: {list(VALID_WINDOWS.keys())}",
        )

    try:
        results = get_top_correlations(db, window=window, n=n, direction="positive")
        return {"window": window, "direction": "positive", "count": len(results), "pairs": results}
    except Exception as exc:
        logger.error("Error computing top positive correlations: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error computing correlations")


@router.get("/top-negative", summary="Top N strongest negative correlations")
def get_top_negative(
    window: str = Query("30D", description="Time window: 7D, 30D, 90D, 180D"),
    n: int = Query(10, ge=1, le=50, description="Number of pairs to return"),
    db: Session = Depends(get_db),
):
    """
    Return the N asset pairs with the strongest negative Pearson correlation
    across all datasets (energy, macro, fundamentals, spreads).

    Response format:
    ```json
    [
      {"asset_1": "dxy", "asset_2": "brent", "correlation": -0.72},
      ...
    ]
    ```
    """
    if window not in VALID_WINDOWS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid window '{window}'. Valid: {list(VALID_WINDOWS.keys())}",
        )

    try:
        results = get_top_correlations(db, window=window, n=n, direction="negative")
        return {"window": window, "direction": "negative", "count": len(results), "pairs": results}
    except Exception as exc:
        logger.error("Error computing top negative correlations: %s", exc)
        raise HTTPException(status_code=500, detail="Internal error computing correlations")


@router.post("/refresh", summary="Force-recompute all correlation matrices")
def refresh_correlations(
    window: str = Query("30D"),
    db: Session = Depends(get_db),
):
    """
    Force-recompute all four matrix types for the given window, bypassing cache.
    Useful after ingesting new data.
    """
    results = {}
    for matrix_type in MATRIX_GROUPS:
        try:
            result = get_matrix(db, window=window, matrix_type=matrix_type, force_refresh=True)
            results[matrix_type] = {
                "labels": result.get("labels", []),
                "size": len(result.get("labels", [])),
            }
        except Exception as exc:
            results[matrix_type] = {"error": str(exc)}

    return {"status": "ok", "window": window, "matrices": results}
