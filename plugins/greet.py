from datetime import datetime
import re
from app import record
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At
from graia.ariadne.model.relationship import Group, Member
from graiax.shortcut.saya import listen, priority

pat = re.compile("^(早上好|早安|中午好|下午好|晚上好).*?")
pat1 = re.compile(".*?(早上好|早安|中午好|下午好|晚上好)$")


@listen(GroupMessage)
@record("greet")
@priority(7)
async def _init_g(app: Ariadne, group: Group, message: MessageChain, member: Member):
    """简单的问好"""
    msg = str(message)
    now = datetime.now()
    if pat.fullmatch(msg) or pat1.fullmatch(msg):
        if 6 <= now.hour < 11:
            reply = "\tο(=•ω＜=)ρ⌒☆\n早上好~"
        elif 11 <= now.hour < 13:
            reply = "\t(o゜▽゜)o☆\n中午好~"
        elif 13 <= now.hour < 18:
            reply = "\t（＾∀＾●）ﾉｼ\n下午好~"
        elif 18 <= now.hour < 24:
            reply = "\tヾ(≧ ▽ ≦)ゝ\n晚上好~"
        else:
            reply = "\t≧ ﹏ ≦\n时候不早了，睡觉吧"
        await app.send_group_message(group, MessageChain(At(member.id), reply))

    if msg.startswith("晚安") or msg.endswith("晚安"):
        if 0 <= now.hour < 6:
            reply = "\t时候不早了，睡觉吧~(￣o￣) . z Z"
        elif 20 < now.hour < 24:
            reply = "\t快睡觉~(￣▽￣)"
        else:
            reply = "\t喂，现在可不是休息的时候╰（‵□′）╯"
        await app.send_group_message(group, MessageChain(At(member.id), reply))
