from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, Group


class Learn(Base):
    __tablename__ = "learn_repeat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    gid: Mapped[str] = mapped_column(ForeignKey(Group.id), nullable=False)
    """群组 ID"""

    key: Mapped[str] = mapped_column(String(256), nullable=False)
    """学习关键词"""

    author: Mapped[str] = mapped_column(String(256), nullable=False)
    """作者"""

    content: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    """学习内容"""
