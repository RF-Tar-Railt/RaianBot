from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, User


class SignRecord(Base):
    __tablename__ = "sign"

    id: Mapped[str] = mapped_column(ForeignKey(User.id), primary_key=True)
    """用户 ID"""

    date: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    """签到日期"""

    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """签到次数"""
