from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from launart import Launart, Service
from loguru import logger
from sqlalchemy.engine.result import Result
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.selectable import TypedReturnsRows

from .manager import DatabaseManager, T_Row
from .model import Base
from .types import EngineOptions


class DatabaseService(Service):
    id: str = "database/init"
    db: DatabaseManager
    get_session: async_sessionmaker[AsyncSession]

    def __init__(self, url: str | URL, engine_options: EngineOptions | None = None) -> None:
        self.db = DatabaseManager(url, engine_options)
        super().__init__()

    @property
    def required(self) -> set[str]:
        return set()

    @property
    def stages(self) -> set[Literal["preparing", "blocking", "cleanup"]]:
        return {"preparing", "blocking", "cleanup"}

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            logger.info("Initializing database...")
            await self.db.initialize()
            self.get_session = self.db.session_factory
            logger.success("Database initialized!")
        async with self.stage("blocking"):
            async with self.db.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                logger.success("Database tables created!")
            await manager.status.wait_for_sigexit()
        async with self.stage("cleanup"):
            await self.db.stop()

    async def execute(self, sql: Executable) -> Result:
        return await self.db.execute(sql)

    async def select_all(self, sql: TypedReturnsRows[tuple[T_Row]]) -> Sequence[T_Row]:
        return await self.db.select_all(sql)

    async def select_first(self, sql: TypedReturnsRows[tuple[T_Row]]) -> T_Row | None:
        return await self.db.select_first(sql)

    async def add(self, row: Base):
        return await self.db.add(row)

    async def add_many(self, rows: Sequence[Base]):
        return await self.db.add_many(rows)

    async def update_or_add(self, row: Base):
        return await self.db.update_or_add(row)

    async def delete_exist(self, row: Base):
        return await self.db.delete_exist(row)

    async def delete_many_exist(self, rows: Sequence[Base]):
        return await self.db.delete_many_exist(rows)
