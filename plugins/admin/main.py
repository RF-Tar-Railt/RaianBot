from __future__ import annotations

from avilla.core import Context
from avilla.core.event import SceneCreated, SceneDestroyed
from avilla.elizabeth.account import ElizabethAccount
from avilla.standard.core.message import MessageReceived
from graia.saya.builtins.broadcast.shortcut import listen, priority
from sqlalchemy import select

from app.database import DatabaseService, Group

from . import debug  # noqa: F401
from . import exception  # noqa: F401


@listen(MessageReceived, SceneCreated)
@priority(7)
async def _init_g(ctx: Context, db: DatabaseService):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return
    if ctx.scene.follows("::guild"):
        return
    account = f"{'.'.join(f'{k}({v})' for k, v in ctx.account.route.items())}"
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.last_value))).one_or_none()
        if not group:
            group = Group(
                id=ctx.scene.last_value,
                platform="qq" if isinstance(ctx.account, ElizabethAccount) else "qqapi",
                accounts=[account],
            )
            session.add(group)
            await session.commit()
            await session.refresh(group)
        elif account not in group.accounts:
            group.accounts.append(account)
            await session.commit()
            await session.refresh(group)


@listen(SceneDestroyed)
async def _remove(ctx: Context, db: DatabaseService):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return
    account = f"{'.'.join(f'{k}({v})' for k, v in ctx.account.route.items())}"
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.last_value))).one_or_none()
        if group:
            if account in group.accounts:
                group.accounts.remove(account)
            if not group.accounts:
                await session.delete(group)
            await session.commit()
