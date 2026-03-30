from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.models.base import Base


class Meal(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True, default="default")
    description = Column(String, nullable=False)
    calories = Column(Float, nullable=True)
    protein = Column(Float, nullable=True)
    carbs = Column(Float, nullable=True)
    fat = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
