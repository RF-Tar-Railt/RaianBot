from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, User


@dataclass
class DrawRecord(Base):
    __tablename__ = "draw"

    id: Mapped[str] = mapped_column(ForeignKey(User.id, ondelete="CASCADE"), primary_key=True)
    """用户 ID"""

    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    """抽签的时间"""

    answer: Mapped[str] = mapped_column(String(64), nullable=False)
    """抽签结果"""
