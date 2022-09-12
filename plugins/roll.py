from arclet.alconna import Args, Empty, Option, Arpamar, CommandMeta
from arclet.alconna.graia import Alconna, alcommand
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.app import Ariadne

from app import Sender
from modules.dice.rd import RD

draw = Alconna(
    r"r( )?{pattern:[0-z|#\+]*}", Args["expect;O", int]["event", str, Empty],
    headers=['.'],
    options=[Option("max", Args["num", int, 100])],
    meta=CommandMeta("模拟coc掷骰功能  注意：该命令以 “.” 为开头", example=".rd100")
)


@alcommand(draw)
async def dice(app: Ariadne, target: Source, sender: Sender, result: Arpamar):
    pattern = result.header['pattern']
    expect = result.main_args.get('expect', -1)
    event = result.main_args.get('event')
    max_num = result.query("max.num", 100)
    rd = RD(pattern)
    try:
        rd_num = rd.roll().total
    except ValueError:
        return await app.send_message(sender, MessageChain("输入有误, 请仔细检查"), quote=target)
    ans = f"进行{event}检定: {rd.pattern}" if event else f"掷骰: {rd.pattern}"
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
