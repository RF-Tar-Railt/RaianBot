from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql.sqltypes import JSON, Boolean, Float, String

_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    """用户 ID"""

    nickname: Mapped[str] = mapped_column(String(64), nullable=True)
    """用户昵称"""

    trust: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    """用户信任度"""


class Group(Base):
    __tablename__ = "group"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    """群组 ID"""

    in_blacklist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    """是否在黑名单中"""

    disabled: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=[])
    """禁用的插件"""
