from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.sql import func
from .base import Base


class CrackSpread(Base):
    """
    Stores computed 3:2:1 crack spread values representing refinery margins.
    Supports WTI-based and Brent-based crack spreads.

    Formula: (2 * gasoline_bbl + 1 * distillate_bbl - 3 * crude) / 3
    RBOB and Heating Oil are quoted $/gallon; multiply by 42 to get $/bbl.
    """
    __tablename__ = "crack_spreads"

    id = Column(Integer, primary_key=True, index=True)
    crude_type = Column(String(10), nullable=False, index=True)  # "wti" or "brent"
    crude_price = Column(Float, nullable=False)                  # $/bbl
    gasoline_price = Column(Float, nullable=False)               # $/bbl (converted)
    distillate_price = Column(Float, nullable=False)             # $/bbl (converted)
    crack_spread = Column(Float, nullable=False)                 # $/bbl
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_crack_spreads_lookup", "crude_type", "timestamp"),
    )
