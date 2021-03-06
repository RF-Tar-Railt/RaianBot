from typing import Union

from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.ariadne.model import Friend, Member, Group, MemberPerm
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Plain
from graia.ariadne.app import Ariadne


def require_admin(only: bool = False):
    from .core import RaianMain

    async def __wrapper__(bot: RaianMain, sender: Union[Friend, Group], target: Union[Member, Friend]):
        if target.id == bot.config.master_id:
            return True
        if not only and isinstance(target, Member) and target.permission in (
                MemberPerm.Administrator, MemberPerm.Owner
        ):
            return True
        text = "权限不足！" if isinstance(sender, Friend) else [At(target.id), Plain("\n权限不足！")]
        await Ariadne.current().send_message(sender, MessageChain(text))
        raise ExecutionStop

    return Depend(__wrapper__)


def require_function(name: str):
    from .core import RaianMain

    def __wrapper__(bot: RaianMain, sender: Union[Friend, Group]):
        data = bot.data
        if isinstance(sender, Friend):
            return True
        if name not in data.funcs:
            return True
        group_data = data.get_group(sender.id)
        if group_data:
            if name in group_data.disabled:
                raise ExecutionStop
            elif group_data.in_blacklist or sender.id in data.cache['blacklist']:
                raise ExecutionStop
        return True

    return Depend(__wrapper__)
