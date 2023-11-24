from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, User


class ArkgachaRecord(Base):
    __tablename__ = "arkgacha"

    id: Mapped[str] = mapped_column(ForeignKey(User.id), primary_key=True)
    """用户 ID"""

    statis: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """保底计数"""

    per: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    """保底概率"""
