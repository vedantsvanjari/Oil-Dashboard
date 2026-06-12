from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.sql import func
from .base import Base


class CorrelationSnapshot(Base):
    """
    Persists computed correlation matrices as JSON blobs.
    Acts as a DB-level cache (recomputed when > 1 hour stale).
    """
    __tablename__ = "correlation_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    window = Column(String(10), nullable=False)       # "7D", "30D", "90D", "180D"
    matrix_type = Column(String(20), nullable=False)  # "product", "spread", "macro", "inventory"
    labels_json = Column(Text, nullable=False)         # JSON array of label strings
    matrix_json = Column(Text, nullable=False)         # JSON 2D array of floats

    __table_args__ = (
        Index("ix_correlation_snapshots_lookup", "window", "matrix_type", "computed_at"),
    )
