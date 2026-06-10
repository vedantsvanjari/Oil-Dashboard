from sqlalchemy import Column, Integer, Date, Float
from app.models.base import Base

class MacroData(Base):
    __tablename__ = "macro_data"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True, nullable=False)
    dxy = Column(Float, nullable=True)
    us10y = Column(Float, nullable=True)
    us2y = Column(Float, nullable=True)
    yield_curve = Column(Float, nullable=True)
