import json
import re
from pathlib import Path
from app import RaianBotService, Sender, Target, accessable, exclusive, record
from arclet.alconna import  Alconna, Arg, Args, CommandMeta, Option, Arparma
from arclet.alconna.graia import Match, alcommand, assign
from arknights_toolkit.record import ArkRecord
from arknights_toolkit.update.record import generate
from arknights_toolkit.images import update_operators
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image

alc = Alconna(
    "抽卡查询",
    Args["count#最近x抽", int, -1],
    Option("绑定", Args[Arg("token", str, seps="\n")]),
    Option("更新", Args["name?#卡池名", str]["limit", bool, True]),
    meta=CommandMeta(
        "明日方舟抽卡数据查询，数据来源为方舟官网",
        usage="""

**token获取方法**：在官网登录后，根据你的服务器，选择复制以下网址中的内容

官服：https://web-api.hypergryph.com/account/info/hg

B服：https://web-api.hypergryph.com/account/info/ak-b

***请在浏览器中获取token，避免在QQ打开的网页中获取，否则可能获取无效token***

再通过 ’渊白抽卡查询 绑定 <你的token>‘ 命令来绑定
        """,
    ),
)

bot = RaianBotService.current()

querier = ArkRecord(
    f"{bot.config.plugin_cache_dir / 'gacha_record'}",
    f"{bot.config.plugin_cache_dir / 'recordpool.json'}",
    f"{bot.config.plugin_cache_dir / 'arkrecord.db'}",
)

alc.shortcut("方舟卡池更新", {"command": f"{bot.config.command.headers[0]}抽卡查询 更新"})


@alcommand(alc)
@assign("$main")
@record("抽卡查询")
@exclusive
@accessable
async def query(app: Ariadne, target: Target, sender: Sender, count: Match[int]):
    try:
        querier.database.read_token_from_db(f"{target.id}")
    except (AssertionError, RuntimeError):
        return await app.send_message(
            sender,
            """您未绑定您的方舟账号 token！

token获取方法：在官网登录后，根据你的服务器，选择复制以下网址中的内容

官服：https://web-api.hypergryph.com/account/info/hg

B服：https://web-api.hypergryph.com/account/info/ak-b

请在浏览器中获取token，避免在QQ打开的网页中获取，否则可能获取无效token

再通过 ’渊白抽卡查询 绑定 <你的token>‘ 命令来绑定
""",
        )
    try:
        warn, file = await querier.user_analysis(f"{target.id}", count.result)
        if warn:
            await app.send_message(sender, warn)
        return await app.send_message(sender, MessageChain(Image(path=file)))
    except RuntimeError as e:
        return await app.send_message(sender, str(e))


@alcommand(alc)
@assign("更新")
@record("抽卡查询")
@exclusive
@accessable
async def update(app: Ariadne, sender: Sender, arp: Arparma):
    if not arp.other_args.get("name"):
        await generate(Path(f"{bot.config.plugin_cache_dir / 'recordpool.json'}").absolute())
    else:
        with open(
            f"{bot.config.plugin_cache_dir / 'recordpool.json'}", "r", encoding="utf-8"
        ) as f:
            pool = json.load(f)
        pool[arp.name] = {"is_exclusive": arp.limit}
    update_operators()
    return await app.send_message(sender, "更新完成")


@alcommand(alc)
@assign("绑定")
@record("抽卡查询")
@exclusive
@accessable
async def bind(app: Ariadne, target: Target, sender: Sender, token: Match[str]):
    if "content" in token.result:
        token.result = re.match(".*content(\")?:(\")?(?P<token>[^{}\"]+).*", token.result)["token"]
    try:
        res = querier.user_token_save(token.result, f"{target.id}")
    except RuntimeError as e:
        return await app.send_message(sender, str(e))
    return await app.send_message(sender, res)