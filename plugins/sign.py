from arclet.alconna import CommandMeta
from arclet.alconna.graia import Alconna, alcommand
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne

from app import RaianMain, record


@record('sign')
@alcommand(Alconna("签到", meta=CommandMeta("在机器人处登记用户信息")), private=False)
async def sign_up(app: Ariadne, sender: Group, member: Member, source: Source, bot: RaianMain):
    """在机器人处登记信息"""
    if bot.data.exist(member.id):
        return await app.send_group_message(
            sender, MessageChain("您已与我签到!\n一人签到一次即可\n之后您不再需要找我签到"),
            quote=source.id
        )
    bot.data.add_user(member.id)
    return await app.send_group_message(
        sender, MessageChain("签到成功！\n现在您可以抽卡与抽签了\n之后您不再需要找我签到"),
        quote=source.id
    )
