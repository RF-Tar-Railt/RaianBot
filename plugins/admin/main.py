from __future__ import annotations

from sqlalchemy import select
from app.database import Group, DatabaseService
from avilla.core import Context
from avilla.standard.core.message import MessageReceived
from graia.saya.builtins.broadcast.shortcut import listen, priority


@listen(MessageReceived)
@priority(7)
async def _init_g(ctx: Context, db: DatabaseService):
    if ctx.client == ctx.scene:
        return
    async with db.get_session() as session:
        group = (
            await session.scalars(
                select(Group)
                .where(Group.id == ctx.scene.last_value)
            )
        ).one_or_none()
        if not group:
            group = Group(id=ctx.scene.last_value)
            session.add(group)
            await session.commit()
            await session.refresh(group)
    # data = interface.data
    # config = interface.config
    # if not data.exist(group.id):
    #     data.add_group(group.id)
    #     data.cache["all_joined_group"].append(group.id)
    #     return await app.send_friend_message(
    #         config.admin.master_id, MessageChain(f"{group.name} 初始配置化完成")
