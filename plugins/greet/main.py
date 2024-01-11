import re
from datetime import datetime

from avilla.core import Context, Message, MessageChain, MessageReceived, Notice
from graia.saya.builtins.broadcast.shortcut import listen, priority

from app.shortcut import accessable, exclusive, is_qqapi_group, record

pat = re.compile("^(早上好|早安|中午好|下午好|晚上好).*?")
pat1 = re.compile(".*?(早上好|早安|中午好|下午好|晚上好)$")


@listen(MessageReceived)
@record("greet")
@priority(9)
@exclusive
@accessable
async def greet(ctx: Context, message: MessageChain, source: Message):
    """简单的问好"""
    msg = str(message.exclude(Notice)).lstrip()
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
        if is_qqapi_group(ctx):
            return await ctx.scene.send_message(reply)
        return await ctx.scene.send_message(reply, reply=source)

    if msg.startswith("晚安") or msg.endswith("晚安"):
        if 0 <= now.hour < 6:
            reply = "\t时候不早了，睡觉吧~(￣o￣) . z Z"
        elif 20 < now.hour < 24:
            reply = "\t快睡觉~(￣▽￣)"
        else:
            reply = "\t喂，现在可不是休息的时候╰（‵□′）╯"
        if is_qqapi_group(ctx):
            return await ctx.scene.send_message(reply)
        return await ctx.scene.send_message(reply, reply=source)
