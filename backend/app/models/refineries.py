from sqlalchemy import Column, Integer, Float, DateTime
from app.models.base import Base

class RefineryData(Base):
    __tablename__ = "refineries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), index=True, unique=True)
    refinery_utilization = Column(Float, default=0.0)
    gross_inputs = Column(Float, default=0.0)
    gasoline_production = Column(Float, default=0.0)
    distillate_production = Column(Float, default=0.0)
