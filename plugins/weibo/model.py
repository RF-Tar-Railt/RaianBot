from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, Group


class WeiboFollower(Base):
    __tablename__ = "weibo"

    id: Mapped[str] = mapped_column(ForeignKey(Group.id), primary_key=True)
    """群组 ID"""

    wid: Mapped[int] = mapped_column(Integer, primary_key=True)
    """微博用户 ID"""
