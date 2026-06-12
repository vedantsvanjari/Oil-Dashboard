# schemas package"""
Pydantic schemas for request validation and OpenAPI response documentation.
Compatible with Pydantic v1 and v2 (FastAPI handles either).
"""
from __future__ import annotations

from typing import Any, List, Optional
from datetime import datetime

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Calendar Spread Schemas
# ---------------------------------------------------------------------------

class CalendarSpreadRecord(BaseModel):
    id: int
    commodity: str
    contract1: str
    contract2: str
    price1: Optional[float]
    price2: Optional[float]
    spread: float
    timestamp: str

    class Config:
        from_attributes = True


class CalendarSpreadStatistics(BaseModel):
    commodity: Optional[str]
    contract1: Optional[str]
    contract2: Optional[str]
    latest: Optional[float]
    daily_change: Optional[float]
    weekly_change: Optional[float]
    monthly_change: Optional[float]
    volatility: Optional[float]
    z_score: Optional[float]
    sample_size: int
    as_of: Optional[str]


class CalendarSpreadHistoryResponse(BaseModel):
    commodity: str
    contract1: str
    contract2: str
    days_requested: int
    count: int
    history: List[CalendarSpreadRecord]


# ---------------------------------------------------------------------------
# Crack Spread Schemas
# ---------------------------------------------------------------------------

class CrackSpreadRecord(BaseModel):
    id: int
    crude_type: str
    crude_price: float
    gasoline_price: float
    distillate_price: float
    crack_spread: float
    timestamp: str

    class Config:
        from_attributes = True


class CrackSpreadStatistics(BaseModel):
    crude_type: str
    latest: Optional[float]
    avg_30d: Optional[float]
    avg_90d: Optional[float]
    volatility: Optional[float]
    trend: Optional[str]
    sample_size: int
    as_of: Optional[str]


class CrackSpreadHistoryResponse(BaseModel):
    crude_type: str
    days_requested: int
    count: int
    history: List[CrackSpreadRecord]


# ---------------------------------------------------------------------------
# Correlation Schemas
# ---------------------------------------------------------------------------

class CorrelationPair(BaseModel):
    asset_1: str
    asset_2: str
    correlation: float


class CorrelationMatrixResponse(BaseModel):
    window: str
    matrix_type: str
    labels: List[str]
    matrix: List[List[Optional[float]]]
    computed_at: str
    cached: bool


class TopCorrelationsResponse(BaseModel):
    window: str
    direction: str
    count: int
    pairs: List[CorrelationPair]


class DatasetDescriptor(BaseModel):
    name: str
    category: str
    source: str
    description: str


class DatasetsResponse(BaseModel):
    total: int
    categories: dict[str, List[DatasetDescriptor]]
