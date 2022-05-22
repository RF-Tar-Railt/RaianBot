from typing import Union

from graia.broadcast.builtin.decorators import Depend
from graia.broadcast.exceptions import ExecutionStop
from graia.ariadne.model import Friend, Member, Group, MemberPerm
from graia.ariadne.message.chain import MessageChain
from graia.ariadne import get_running


def require_admin(*ids_: int):
    async def __wrapper__(sender: Union[Friend, Group], target: Union[Member, Friend]):
        if target.id in ids_:
            return True
        if isinstance(target, Member) and target.permission in (MemberPerm.Administrator, MemberPerm.Owner):
            return True
        await get_running().sendMessage(sender, MessageChain.create("权限不足！"))
        raise ExecutionStop

    return Depend(__wrapper__)
