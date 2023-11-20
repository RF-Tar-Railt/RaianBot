from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, User


class DrawRecord(Base):
    __tablename__ = "draw"

    id: Mapped[str] = mapped_column(ForeignKey(User.id), primary_key=True)
    """用户 ID"""

    date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    """抽签的时间"""

    answer: Mapped[str] = mapped_column(String(64), nullable=False)
    """抽签结果"""
