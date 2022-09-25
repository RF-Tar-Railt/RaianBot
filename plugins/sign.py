from datetime import datetime

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
    today = datetime.now()
    if not bot.data.exist(member.id):
        bot.data.add_user(member.id)
        user = bot.data.get_user(member.id)
        user.additional['sign_info'] = [today.month, today.day]
        user.trust += 1
        bot.data.update_user(user)
        return await app.send_group_message(
            sender, MessageChain(f"签到成功！\n当前信赖值：{user.trust}\n初次签到提醒您：\n现在您可以抽卡与抽签了"),
            quote=source.id
        )
    user = bot.data.get_user(member.id)
    if not user.additional.get('sign_info'):
        user.additional['sign_info'] = [-1, -1]
    local_day = user.additional['sign_info']
    if local_day[1] == today.day and local_day[0] == today.month:
        return await app.send_group_message(
            sender, MessageChain("您今天已与我签到!"),
            quote=source.id
        )
    user.additional['sign_info'] = [today.month, today.day]
    if user.trust < int(bot.config.plugin.get('sign_max', 200)):
        user.trust += 1
        await app.send_group_message(
            sender, MessageChain(f"签到成功！\n当前信赖值：{user.trust}"),
            quote=source.id
        )
    else:
        await app.send_group_message(
            sender, MessageChain(f"签到成功！\n您的信赖已满！"),
            quote=source.id
        )
    bot.data.update_user(user)
