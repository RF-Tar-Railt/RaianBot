from __future__ import annotations

import contextlib
from collections.abc import AsyncGenerator, Sequence
from typing import TYPE_CHECKING, Any, Literal

from launart import Service
from loguru import logger
from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session
from sqlalchemy.sql.base import Executable
from sqlalchemy.sql.selectable import TypedReturnsRows

from .manager import DatabaseManager, T_Row
from .model import Base


class Database:
    db: "DatabaseManager"

    def __init__(self, db: "DatabaseManager"):
        self.db = db

    if not TYPE_CHECKING:

        def __getattr__(self, name: str) -> Any:
            return self.db.__getattribute__(name)

    @contextlib.asynccontextmanager
    async def async_session(self) -> AsyncGenerator[async_scoped_session[AsyncSession], Any]:
        ...

    async def exec(self, sql: Executable) -> Result:
        ...

    async def select_all(self, sql: TypedReturnsRows[tuple[T_Row]]) -> Sequence[T_Row]:
        ...

    async def select_first(self, sql: TypedReturnsRows[tuple[T_Row]]) -> T_Row | None:
        ...

    async def add(self, row: Base):
        ...

    async def add_many(self, rows: Sequence[Base]):
        ...

    async def update_or_add(self, row: Base):
        ...

    async def delete_exist(self, row: Base):
        ...

    async def delete_many_exist(self, rows: Sequence[Base]):
        ...


class DatabaseService(Service):
    id: str = "database/init"
    db: DatabaseManager

    def __init__(self, url: str = "sqlite+aiosqlite:///data/harmoland-console.db") -> None:
        self.db = DatabaseManager(url)
        super().__init__()

    def get_interface(self) -> Database:
        return Database(self.db)

    @property
    def required(self) -> set[str]:
        return set()

    @property
    def stages(self) -> set[Literal["preparing", "blocking", "cleanup"]]:
        return {"preparing", "cleanup"}

    async def launch(self, _):
        logger.info("Initializing database...")
        await self.db.initialize()
        logger.success("Database initialized!")

        async with self.stage("preparing"):
            ...

        async with self.stage("cleanup"):
            await self.db.stop()
