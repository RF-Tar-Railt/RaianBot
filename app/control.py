from __future__ import annotations

from typing import Any

from avilla.core import Context
from avilla.core.account import BaseAccount
from avilla.core.elements import Notice, Text
from avilla.core.event import AvillaEvent
from avilla.elizabeth.account import ElizabethAccount
from avilla.standard.core.privilege import Privilege
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from sqlalchemy.sql import select

from .config import BotConfig
from .core import RaianBotService
from .database import DatabaseService, Group


def require_admin(only: bool = False, __record: Any = None):
    async def __wrapper__(
        interface: DispatcherInterface[AvillaEvent], serv: RaianBotService, bot: BotConfig, ctx: Context
    ):
        if not isinstance(ctx.account, ElizabethAccount):
            if ctx.scene.pattern.get("group"):
                return True
            if ctx.scene.pattern.get("friend"):
                return True
            private = "user" in ctx.scene.pattern
        else:
            private = "friend" in ctx.scene.pattern
        id_ = f"{id(interface.event)}"
        cache = serv.cache.setdefault("$admin", {})
        if ctx.client.last_value in [bot.master_id, bot.account]:
            serv.cache.pop("$admin", None)
            return True
        pri = await ctx.client.pull(Privilege)
        if not only and (pri.available or ctx.client.last_value in bot.admins):
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
            group = (await session.scalars(select(Group).where(Group.id == ctx.scene.last_value))).one_or_none()
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
    def __wrapper__(serv: RaianBotService, bot: BotConfig):
        if path in bot.disabled or path in serv.config.plugin.disabled:
            raise ExecutionStop
        return True

    return Depend(__wrapper__)


# def check_exclusive():
#     def __wrapper__(app: Ariadne, target: Union[Friend, Member], event: MiraiEvent):
#         from .core import RaianBotInterface
#
#         interface = app.launch_manager.get_interface(RaianBotInterface)
#
#         if target.id in interface.base_config.bots:
#             raise ExecutionStop
#
#         if isinstance(event, GroupMessage) and len(interface.base_config.bots) > 1:
#             seed = int(event.source.id + datetime.now().timestamp())
#             bots = {k : v for k, v in DataInstance.get().items() if v.exist(event.sender.group.id)}
#             if len(bots) > 1:
#                 default = DataInstance.get()[interface.base_config.default_account]
#                 excl = default.cache.setdefault("$exclusive", {})
#                 if str(event.source.id) not in excl:
#                     excl.clear()
#                     rand = random.Random()
#                     rand.seed(seed)
#                     choice = rand.choice(list(bots.keys()))
#                     excl[str(event.source.id)] = choice
#                 if excl[str(event.source.id)] != app.account:
#                     raise ExecutionStop
#
#         return True
#
#     return Depend(__wrapper__)
