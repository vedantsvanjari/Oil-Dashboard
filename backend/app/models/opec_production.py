"""
opec_production.py
------------------
SQLAlchemy model for the opec_production table.

Stores OPEC Total Petroleum Supply (mb/d) sourced from the EIA Short-Term
Energy Outlook (STEO) API, series PAPR_OPEC.

Each row represents one calendar month.  report_month is stored as a
date-like string in YYYY-MM format and carries a unique constraint so that
upserts never create duplicates.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index, UniqueConstraint
from sqlalchemy.sql import func
from .base import Base


class OpecProduction(Base):
    """
    opec_production
    ---------------
    id              – auto-increment PK
    report_month    – YYYY-MM string (e.g. '2024-06') — UNIQUE
    production_mbd  – OPEC total petroleum supply in million barrels per day
    source_report   – human-readable description of the data series / API used
    created_at      – row insertion timestamp (UTC, server-generated)
    """

    __tablename__ = "opec_production"

    id             = Column(Integer, primary_key=True, index=True)
    report_month   = Column(String(7), nullable=False, unique=True, index=True)
    production_mbd = Column(Float, nullable=False)
    source_report  = Column(String(200), nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("report_month", name="uq_opec_production_month"),
        Index("ix_opec_production_month", "report_month"),
    )

    def __repr__(self) -> str:
        return f"<OpecProduction month={self.report_month} prod={self.production_mbd:.3f} mb/d>"
