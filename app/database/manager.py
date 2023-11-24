from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar, cast

from sqlalchemy.engine.result import Result
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.selectable import TypedReturnsRows

from .model import Base
from .types import EngineOptions

# sqlite_url = 'sqlite+aiosqlite:///data/redbot.db'
# mysql_url = 'mysql+aiomysql://user:pass@hostname/dbname?charset=utf8mb4
T_Row = TypeVar("T_Row", bound=Base)


class DatabaseManager:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

    def __init__(self, url: str | URL, engine_options: EngineOptions | None = None):
        if engine_options is None:
            engine_options = {"echo": "debug", "pool_pre_ping": True}
        self.engine = create_async_engine(url, **engine_options)

    async def initialize(self, session_options: dict[str, Any] | None = None):
        """初始化数据库

        运行前需确保所有被用到的数据库表模型都至少被 import 过一次，且均继承了 Base 类
        """
        if session_options is None:
            session_options = {"expire_on_commit": False}
        self.session_factory = async_sessionmaker(self.engine, **session_options)

    async def stop(self, close: bool = True):
        """释放连接池中的链接

        Dispose of the connection pool used by this Engine.

        A new connection pool is created immediately after the old one has been disposed.
        The previous connection pool is disposed either actively,
        by closing out all currently checked-in connections in that pool,
        or passively, by losing references to it but otherwise not closing any connections.
        The latter strategy is more appropriate for an initializer in a forked Python process.
        """
        # for AsyncEngine created in function scope, close and
        # clean-up pooled connections
        await self.engine.dispose(close)

    async def execute(self, sql: Executable) -> Result:
        """执行 SQL 命令"""
        async with self.session_factory() as session:
            return await session.execute(sql)

    async def select_all(self, sql: TypedReturnsRows[tuple[T_Row]]) -> Sequence[T_Row]:
        async with self.session_factory() as session:
            result = await session.scalars(sql)
        return result.all()

    async def select_first(self, sql: TypedReturnsRows[tuple[T_Row]]) -> T_Row | None:
        async with self.session_factory() as session:
            result = await session.scalars(sql)
        return cast("T_Row | None", result.first())

    async def add(self, row: Base) -> None:
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)

    async def add_many(self, rows: Sequence[Base]):
        async with self.session_factory() as session:
            session.add_all(rows)
            await session.commit()
            for row in rows:
                await session.refresh(row)

    async def update_or_add(self, row: Base):
        async with self.session_factory() as session:
            await session.merge(row)
            await session.commit()
            await session.refresh(row)

    async def delete_exist(self, row: Base):
        async with self.session_factory() as session:
            await session.delete(row)

    async def delete_many_exist(self, rows: Sequence[Base]):
        async with self.session_factory() as session:
            for row in rows:
                await session.delete(row)
