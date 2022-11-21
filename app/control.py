from typing import Union, Optional

from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.ariadne.model import Friend, Member, Group, MemberPerm
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from graia.ariadne.event.message import MessageEvent
from graia.ariadne.app import Ariadne


def require_admin(only: bool = False):
    async def __wrapper__(
        app: Ariadne,
        sender: Union[Friend, Group],
        target: Union[Member, Friend],
        event: Optional[MessageEvent],
    ):
        from .core import RaianBotInterface

        bot = app.launch_manager.get_interface(RaianBotInterface)
        id_ = id(event) if event else 0
        cache = bot.data.cache.setdefault("$admin", set())
        if target.id == bot.config.admin.master_id:
            bot.data.cache.pop("$admin", None)
            return True
        if not only and (
            (
                isinstance(target, Member)
                and target.permission in (MemberPerm.Administrator, MemberPerm.Owner)
            )
            or target.id in bot.config.admin.admins
        ):
            bot.data.cache.pop("$admin", None)
            return True
        text = (
            "权限不足！" if isinstance(sender, Friend) else [At(target.id), Plain("\n权限不足！")]
        )
        if id_ not in cache:
            cache.clear()
            cache.add(id_)
            await Ariadne.current().send_message(sender, MessageChain(text))
        raise ExecutionStop

    return Depend(__wrapper__)


def require_function(name: str):
    def __wrapper__(app: Ariadne, sender: Union[Friend, Group]):
        from .core import RaianBotInterface

        data = app.launch_manager.get_interface(RaianBotInterface).data
        if isinstance(sender, Friend):
            return True
        if name not in data.funcs:
            return True
        if group_data := data.get_group(sender.id):
            if name in group_data.disabled:
                raise ExecutionStop
            elif group_data.in_blacklist or sender.id in data.cache.get("blacklist", []):
                raise ExecutionStop
        return True

    return Depend(__wrapper__)
