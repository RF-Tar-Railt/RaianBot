from __future__ import annotations

import random
from datetime import datetime
from typing import Any

from avilla.core import Context
from avilla.core.account import BaseAccount
from avilla.core.elements import Notice, Text
from avilla.elizabeth.account import ElizabethAccount
from avilla.standard.core.message import MessageReceived
from avilla.standard.core.privilege import Privilege
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from sqlalchemy.sql import select

from .config import BotConfig
from .core import RaianBotService
from .database import DatabaseService, Group


def require_admin(only: bool = False, __record: Any = None):
    async def __wrapper__(event: MessageReceived, serv: RaianBotService, bot: BotConfig, ctx: Context):
        if not isinstance(ctx.account, ElizabethAccount):
            if ctx.scene.pattern.get("group"):
                return True
            if ctx.scene.pattern.get("friend"):
                return True
            private = "user" in ctx.scene.pattern
        else:
            private = "friend" in ctx.scene.pattern
        id_ = f"{id(event)}"
        cache = serv.cache.setdefault("$admin", {})
        if ctx.client.user in [bot.master_id, bot.account]:
            serv.cache.pop("$admin", None)
            return True
        pri = await ctx.client.pull(Privilege)
        if not only and (pri.available or ctx.client.user in bot.admins):
            serv.cache.pop("$admin", None)
            return True
        text = "权限不足！" if private else [Notice(ctx.client), Text("\n权限不足！")]
        if id_ not in cache:
            cache.clear()
            cache[id_] = True
            await ctx.scene.send_message(text)
        raise ExecutionStop

    return Depend(__wrapper__)


def require_function(name: str):
    async def __wrapper__(ctx: Context, bot: RaianBotService, db: DatabaseService):
        if ctx.scene == ctx.client:
            return True
        if name not in bot.functions:
            return True
        async with db.get_session() as session:
            group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
            if group:
                if name in group.disabled:
                    raise ExecutionStop
                elif group.in_blacklist:
                    raise ExecutionStop
            return True

    return Depend(__wrapper__)


def require_account(atype: type[BaseAccount] | tuple[type[BaseAccount], ...]):
    async def __wrapper__(ctx: Context):
        if isinstance(ctx.account, atype):
            return True
        raise ExecutionStop

    return __wrapper__


def check_disabled(path: str):
    def __wrapper__(serv: RaianBotService):
        if path in serv.config.plugin.disabled:
            raise ExecutionStop
        return True

    return Depend(__wrapper__)


def check_exclusive():
    async def __wrapper__(event: MessageReceived, serv: RaianBotService, ctx: Context):
        if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
            return True
        if len(serv.config.bots) > 1:
            seed = datetime.now().timestamp()
            async with serv.db.get_session() as session:
                group = (
                    await session.scalars(
                        select(Group)
                        .where(Group.id == ctx.scene.channel)
                        .where(Group.platform == ("qq" if isinstance(ctx.account, ElizabethAccount) else "qqapi"))
                    )
                ).one_or_none()
                if not group or len(group.accounts) < 2:
                    return True
                # if event.message.content and isinstance(event.message.content[0], Notice):
                #     notice: Notice = event.message.content.get_first(Notice)
                #     if notice.target.last_value == ctx.self.last_value:
                #         return True
                excl = serv.cache.setdefault("$exclusive", {})
                if event.message.to_selector() not in excl:
                    excl.clear()
                    rand = random.Random()
                    rand.seed(seed)
                    choice = rand.choice(group.accounts)
                    excl[event.message.id] = choice
                elif not ctx.account.route.follows(excl[event.message.to_selector()]):
                    raise ExecutionStop

        return True

    return Depend(__wrapper__)
