import contextlib
import re
from io import BytesIO

from app import Sender, accessable, exclusive, record, RaianBotService
from arclet.alconna import Alconna, Arg, Args, Arparma, CommandMeta, Field, Option, MultiVar
from arclet.alconna.graia import alcommand
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from library.translate import YoudaoTrans, TencentTrans
from library.wecd import gen_counting_down, gen_gif
from nepattern import RegexPattern

from plugins.config.dialog import DialogConfig

counting = RegexPattern(r"(?P<num>\d+)(?P<unit>.+)", alias="倒计时")
cd = Alconna(
    [""],
    "倒计时",
    Arg("content#中文内容", str),
    Arg("state", str, "还有"),
    Arg("count", counting, Field(counting.match("5秒"), alias="5秒"), notice="倒计时"),
    Option("-gif", help_text="是否为gif形式"),
    Option("英文", Args["en",  MultiVar(str)] / "\n", help_text="英文内容，不设置则自动翻译"),
    meta=CommandMeta("流浪地球倒计时", usage="注意: 该命令不需要 “渊白” 开头", example="倒计时 离开学 还剩 1天"),
)

bot = RaianBotService.current()
config: DialogConfig = bot.config.plugin.get(DialogConfig)
trans = (
    TencentTrans(
        bot.config.platform.tencentcloud_secret_id,
        bot.config.platform.tencentcloud_secret_key
    ) if config.tencent else YoudaoTrans()
)


@alcommand(cd)
@record("wecd")
@exclusive
@accessable
async def draw(app: Ariadne, sender: Sender, arp: Arparma):
    content = arp.content
    start = arp.state
    count = arp.count.groupdict()
    with contextlib.suppress(Exception):
        count = counting.match(start).groupdict()
        start = "还有"
    en = "\n".join(arp.query("英文.en", [])) or (
        f"{await trans.trans(content, 'en')}\n"
        f"{await trans.trans(f'''{start}{count['num']}{count['unit']}''', 'en')}"
    )
    if arp.components.get("gif"):
        if int(count["num"]) > 60:
            return await app.send_message(sender, "这个数字太大了！")
        data = gen_gif(content, start, int(count["num"]), count["unit"], en)
        return await app.send_message(sender, MessageChain(Image(data_bytes=data)))
    img = gen_counting_down(content, start, int(count["num"]), count["unit"], en)
    bio = BytesIO()
    img.save(
        bio,
        "JPEG",
        quality=95,
        subsampling=2,
        qtables="web_high",
    )
    return await app.send_message(sender, MessageChain(Image(data_bytes=bio.getvalue())))
