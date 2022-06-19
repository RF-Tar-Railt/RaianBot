from typing import Union
from arclet.alconna import Args, Empty, Option
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from app import RaianMain
from modules.dice.rd import RD

channel = Channel.current()
bot = RaianMain.current()
draw = Alconna(
    r"r{pattern:[0-z|#\+]*}", Args["expect;O", int]["event", str, Empty],
    headers=bot.config.command_prefix,
    options=[Option("max", Args["num", int, 100])],
    help_text=f"模拟coc掷骰功能",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=draw, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def test2(
        app: Ariadne,
        target: Source,
        sender: Union[Group, Friend],
        result: AlconnaProperty
):
    arp = result.result
    pattern = arp.header['pattern']
    expect = arp.main_args.get('expect', -1)
    event = arp.main_args.get('event')
    max_num = arp.query("max.num", 100)
    rd = RD(pattern)
    try:
        rd_num = rd.roll().total
    except ValueError:
        return await app.send_message(sender, MessageChain("输入有误, 请仔细检查"), quote=target)
    if event:
        ans = f"进行{event}检定: {rd.pattern}"
    else:
        ans = f"掷骰: {rd.pattern}"
    if expect > 0:
        if rd_num == max_num or (expect < max_num / 2 and rd_num >= 0.96 * max_num):
            ans += f"={rd_num}/{expect}, 大失败"
        elif rd_num > expect:
            ans += f"={rd_num}/{expect}, 失败"
        elif expect / 2 < rd_num <= expect:
            ans += f"={rd_num}/{expect}, 常规成功"
        elif expect / 5 < rd_num <= expect / 2:
            ans += f"={rd_num}/{expect}, 困难成功"
        elif 1 < rd_num <= expect / 5:
            ans += f"={rd_num}/{expect}, 极难成功"
        else:
            ans += f"={rd_num}/{expect}, 大成功"
    else:
        ans += f"={rd_num}"
    await app.send_message(sender, MessageChain(ans), quote=target)
