from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.sql import func
from .base import Base


class CalendarSpread(Base):
    """
    Stores computed calendar spread values (nearby minus deferred contract).
    Supports WTI and Brent across M1-M2, M2-M3, M3-M4, M1-M6, M1-M12 pairs.
    """
    __tablename__ = "calendar_spreads"

    id = Column(Integer, primary_key=True, index=True)
    commodity = Column(String(10), nullable=False, index=True)   # "wti" or "brent"
    contract1 = Column(String(10), nullable=False)               # "M1", "M2", etc.
    contract2 = Column(String(10), nullable=False)               # "M2", "M3", etc.
    price1 = Column(Float, nullable=True)                        # nearby price ($/bbl)
    price2 = Column(Float, nullable=True)                        # deferred price ($/bbl)
    spread = Column(Float, nullable=False)                       # price1 - price2
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Composite index for the most common query pattern
    __table_args__ = (
        Index(
            "ix_calendar_spreads_lookup",
            "commodity", "contract1", "contract2", "timestamp"
        ),
    )
