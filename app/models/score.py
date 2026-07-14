from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, func
from app.models import Base


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_id = Column(String(64), nullable=False, index=True)
    score = Column(Integer, nullable=False, default=0)
    game_data = Column(JSON, nullable=True)
    played_at = Column(DateTime(timezone=True), server_default=func.now())
