import random
from datetime import datetime
from typing import NamedTuple
from arclet.alconna import CommandMeta
from arclet.alconna.graia import Alconna, alcommand
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne

from app import RaianBotInterface, record, meta_export
from plugins.config.sign import SignConfig


class sign_info(NamedTuple):
    month: int
    day: int


meta_export(user_meta=[sign_info])


@alcommand(Alconna("签到", meta=CommandMeta("在机器人处登记用户信息")), private=False)
@record('sign')
async def sign_up(app: Ariadne, sender: Group, member: Member, source: Source, bot: RaianBotInterface):
    """在机器人处登记信息"""
    today = datetime.now()
    if not bot.data.exist(member.id):
        user = bot.data.add_user(member.id)
        user.set(sign_info(today.month, today.day))
        user.trust += 1
        bot.data.update_user(user)
        return await app.send_group_message(
            sender, MessageChain(f"签到成功！\n当前信赖值：{user.trust}\n初次签到提醒您：\n现在您可以抽卡与抽签了"),
            quote=source.id
        )
    user = bot.data.get_user(member.id)
    info = user.get(sign_info, sign_info(-1, -1))
    if info.day == today.day and info.month == today.month:
        return await app.send_group_message(
            sender, MessageChain("您今天已与我签到!"),
            quote=source.id
        )
    user.set(sign_info(today.month, today.day))
    if user.trust < int(bot.config.plugin.get(SignConfig).max):
        user.trust += (random.randint(1, 10) / 6.25)
        await app.send_group_message(
            sender, MessageChain(f"签到成功！\n当前信赖值：{user.trust:.3f}"),
            quote=source.id
        )
    else:
        await app.send_group_message(
            sender, MessageChain(f"签到成功！\n您的信赖已满！"),
            quote=source.id
        )
    bot.data.update_user(user)
