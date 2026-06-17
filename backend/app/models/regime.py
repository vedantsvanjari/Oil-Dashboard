from sqlalchemy import Column, Integer, Float, String, DateTime
from app.models.base import Base

class RegimeAnalysis(Base):
    __tablename__ = "regime_analysis"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    
    # M1 to M14
    m1 = Column(Float)
    m2 = Column(Float)
    m3 = Column(Float)
    m4 = Column(Float)
    m5 = Column(Float)
    m6 = Column(Float)
    m7 = Column(Float)
    m8 = Column(Float)
    m9 = Column(Float)
    m10 = Column(Float)
    m11 = Column(Float)
    m12 = Column(Float)
    m13 = Column(Float)
    m14 = Column(Float)

    # Spreads
    m1_m2 = Column(Float)
    m1_m3 = Column(Float)
    m1_m6 = Column(Float)
    m1_m12 = Column(Float)
    m1_m14 = Column(Float)

    # Butterflies
    fly_123 = Column(Float)
    fly_234 = Column(Float)
    fly_345 = Column(Float)

    # Curve Features
    front_slope = Column(Float)
    mid_slope = Column(Float)
    long_slope = Column(Float)
    curvature = Column(Float)

    # Regime Logic
    regime = Column(String, index=True)
    regime_score = Column(Float)
