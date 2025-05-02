from dataclasses import dataclass

from sqlalchemy import BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, Group


@dataclass
class WeiboFollower(Base):
    __tablename__ = "weibo"

    id: Mapped[str] = mapped_column(ForeignKey(Group.id, ondelete="CASCADE"), primary_key=True)
    """群组 ID"""

    wid: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    """微博用户 ID"""
