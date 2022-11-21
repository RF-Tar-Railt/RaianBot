from datetime import datetime

from app import record
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At
from graia.ariadne.model.relationship import Group, Member
from graiax.shortcut.saya import listen, priority


@listen(GroupMessage)
@record("greet")
@priority(7)
async def _init_g(app: Ariadne, group: Group, message: MessageChain, member: Member):
    """简单的问好"""
    msg = message.display
    now = datetime.now()
    if (
        msg.startswith("早上好")
        or msg.startswith("早安")
        or msg.startswith("中午好")
        or msg.startswith("下午好")
        or msg.startswith("晚上好")
    ):
        if 6 <= now.hour < 11:
            reply = "\t早上好~"
        elif 11 <= now.hour < 13:
            reply = "\t中午好~"
        elif 13 <= now.hour < 18:
            reply = "\t下午好~"
        elif 18 <= now.hour < 24:
            reply = "\t晚上好~"
        else:
            reply = "\t时候不早了，睡觉吧"
        await app.send_group_message(group, MessageChain(At(member.id), reply))

    if msg.startswith("晚安"):
        # if str(member.id) in sign_info:
        #     sign_info[str(member.id)]['trust'] += 1 if sign_info[str(member.id)]['trust'] < 200 else 0
        #     sign_info[str(member.id)]['interactive'] += 1
        if 0 <= now.hour < 6:
            reply = "\t时候不早了，睡觉吧~(￣o￣) . z Z"
        elif 20 < now.hour < 24:
            reply = "\t快睡觉~(￣▽￣)"
        else:
            reply = "\t喂，现在可不是休息的时候╰（‵□′）╯"
        await app.send_group_message(group, MessageChain(At(member.id), reply))
