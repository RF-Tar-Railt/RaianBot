from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, Group


class Learn(Base):
    __tablename__ = "learn_repeat"

    id: Mapped[str] = mapped_column(ForeignKey(Group.id), primary_key=True)
    """群组 ID"""

    key: Mapped[str] = mapped_column(String(256), nullable=False)
    """学习关键词"""

    author: Mapped[str] = mapped_column(String(256), nullable=False)
    """作者"""

    content: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    """学习内容"""
