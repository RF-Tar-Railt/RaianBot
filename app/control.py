from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Optional, Union

from avilla.core import Context
from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from loguru import logger
from sqlalchemy.sql import select

from .core import RaianBotService
from .database import DatabaseService, Group



def require_admin(only: bool = False, __record: Any = None):
    async def __wrapper__(
        app: Ariadne,
        sender: Union[Friend, Group],
        target: Union[Member, Friend],
        event: Optional[MessageEvent],
    ):
        from .core import RaianBotInterface

        interface = app.launch_manager.get_interface(RaianBotInterface)
        id_ = f"{id(event)}" if event else "_"
        cache = interface.data.cache.setdefault("$admin", {})
        if target.id in [interface.config.admin.master_id, interface.config.account]:
            interface.data.cache.pop("$admin", None)
            return True
        if not only and (
            (isinstance(target, Member) and target.permission in (MemberPerm.Administrator, MemberPerm.Owner))
            or target.id in interface.config.admin.admins
        ):
            interface.data.cache.pop("$admin", None)
            return True
        text = "权限不足！" if isinstance(sender, Friend) else [At(target.id), Plain("\n权限不足！")]
        logger.debug(f"permission denied for {sender.id} in {__record}")
        if id_ not in cache:
            cache.clear()
            cache[id_] = True
            await Ariadne.current().send_message(sender, MessageChain(text))
        raise ExecutionStop

    return Depend(__wrapper__)


def require_function(name: str):
    async def __wrapper__(ctx: Context, bot: RaianBotService, db: DatabaseService):
        if ctx.scene == ctx.client:
            return True
        if name not in bot.functions:
            return True
        async with db.get_session() as session:
            group = (
                await session.scalars(
                    select(Group)
                    .where(Group.id == ctx.scene.last_value)
                )
            ).one_or_none()
            if group:
                if name in group.disabled:
                    raise ExecutionStop
                elif group.in_blacklist:
                    raise ExecutionStop
            return True

    return Depend(__wrapper__)


def check_disabled(path: str):
    def __wrapper__(app: Ariadne):
        from .core import RaianBotInterface

        config = app.launch_manager.get_interface(RaianBotInterface).config
        if path in config.disabled:
            raise ExecutionStop
        return True

    return Depend(__wrapper__)


def check_exclusive():
    def __wrapper__(app: Ariadne, target: Union[Friend, Member], event: MiraiEvent):
        from .core import RaianBotInterface

        interface = app.launch_manager.get_interface(RaianBotInterface)

        if target.id in interface.base_config.bots:
            raise ExecutionStop

        if isinstance(event, GroupMessage) and len(interface.base_config.bots) > 1:
            seed = int(event.source.id + datetime.now().timestamp())
            bots = {k : v for k, v in DataInstance.get().items() if v.exist(event.sender.group.id)}
            if len(bots) > 1:
                default = DataInstance.get()[interface.base_config.default_account]
                excl = default.cache.setdefault("$exclusive", {})
                if str(event.source.id) not in excl:
                    excl.clear()
                    rand = random.Random()
                    rand.seed(seed)
                    choice = rand.choice(list(bots.keys()))
                    excl[str(event.source.id)] = choice
                if excl[str(event.source.id)] != app.account:
                    raise ExecutionStop

        return True

    return Depend(__wrapper__)
