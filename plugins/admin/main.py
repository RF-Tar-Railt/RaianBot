from __future__ import annotations

from avilla.core import Context
from avilla.core.event import RelationshipCreated
from avilla.standard.core.message import MessageReceived
from graia.saya.builtins.broadcast.shortcut import listen, priority
from sqlalchemy import select

from app.database import DatabaseService, Group


@listen(MessageReceived, RelationshipCreated)
@priority(7)
async def _init_g(ctx: Context, db: DatabaseService):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.last_value))).one_or_none()
        if not group:
            group = Group(id=ctx.scene.last_value)
            session.add(group)
            await session.commit()
            await session.refresh(group)
