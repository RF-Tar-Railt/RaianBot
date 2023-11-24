from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SKAutoSignRecord(Base):
    __tablename__ = "sk_autosign"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    """用户 ID"""

    token: Mapped[str] = mapped_column(String(256), nullable=False)
    """森空岛token"""


class SKAutoSignResultRecord(Base):
    __tablename__ = "sk_autosign_result"

    id: Mapped[str] = mapped_column(ForeignKey(SKAutoSignRecord.id), primary_key=True)
    """用户 ID"""

    uid: Mapped[str] = mapped_column(String(256), primary_key=True)
    """玩家 ID"""

    date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    """签到时间"""

    result: Mapped[dict] = mapped_column(JSON, nullable=False, default={})
    """结果"""
