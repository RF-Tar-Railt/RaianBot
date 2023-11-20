from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, Group


class CocRule(Base):
    __tablename__ = "coc"

    id: Mapped[str] = mapped_column(ForeignKey(Group.id), primary_key=True)
    """群组 ID"""

    rule: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    """房规"""
