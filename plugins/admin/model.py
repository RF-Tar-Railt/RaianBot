from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BlacklistCache(Base):
    __tablename__ = "blacklist"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    """群组 ID"""

    in_blacklist: Mapped[bool] = mapped_column(Boolean, default=False)
    """是否在黑名单中"""
