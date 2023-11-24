import json
import re
from pathlib import Path
from secrets import token_hex

from arclet.alconna import Alconna, Arg, Args, Arparma, CommandMeta, Option
from arclet.alconna.graia import Match, alcommand, assign
from arknights_toolkit.images import update_operators
from arknights_toolkit.record import ArkRecord
from arknights_toolkit.update.record import generate
from avilla.core import ActionFailed, Context, Picture, RawResource

from app.core import RaianBotService
from app.image import md2img
from app.shortcut import accessable, picture, record

alc = Alconna(
    "抽卡查询",
    Args["count#最近x抽", int, -1],
    Option("绑定", Args[Arg("token", str, seps="\n")], compact=True),
    Option("更新", Args["name?#卡池名", str]["limit", bool, True]),
    meta=CommandMeta(
        "明日方舟抽卡数据查询，数据来源为方舟官网",
        usage="""

**token获取方法**：在官网登录后，根据你的服务器，选择复制以下网址中的内容

官服：https://web-api.hypergryph.com/account/info/hg

B服：https://web-api.hypergryph.com/account/info/ak-b

***请在浏览器中获取token，避免在QQ打开的网页中获取，否则可能获取无效token***

再通过 ’渊白抽卡查询 绑定 你的token‘ 命令来绑定
        """,
        compact=True,
    ),
)

bot = RaianBotService.current()

querier = ArkRecord(
    f"{bot.config.plugin_data_dir / 'gacha_record'}",
    f"{bot.config.plugin_data_dir / 'recordpool.json'}",
    f"{bot.config.plugin_data_dir / 'arkrecord.db'}",
    proxy=bot.config.proxy,
)

alc.shortcut("方舟卡池更新", {"command": "抽卡查询 更新", "prefix": True})


@alcommand(alc)
@assign("$main")
@record("抽卡查询")
# @exclusive
@accessable
async def query(ctx: Context, count: Match[int]):
    try:
        querier.database.read_token_from_db(f"{ctx.client.last_key}")
    except (AssertionError, RuntimeError):
        img = await md2img(
            """\
您未绑定您的方舟账号 token！

token获取方法：在官网登录后，根据你的服务器，选择复制以下网址中的内容

官服：https://web-api.hypergryph.com/account/info/hg

B服：https://web-api.hypergryph.com/account/info/ak-b

请在浏览器中获取token，避免在QQ打开的网页中获取，否则可能获取无效token

再通过 ’渊白抽卡查询 绑定 你的token‘ 命令来绑定
"""
        )
        try:
            return await ctx.scene.send_message(Picture(RawResource(img)))
        except Exception:
            url = await bot.upload_to_cos(img, f"gacha_record_help_{token_hex(16)}.jpg")
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed:
                return await ctx.scene.send_message(picture(url, ctx))
    try:
        warn, file = await querier.user_analysis(f"{ctx.client.last_key}", count.result)
        if warn:
            await ctx.scene.send_message(warn)
        try:
            return await ctx.scene.send_message(Picture(file))
        except Exception:
            url = await bot.upload_to_cos(file.read_bytes(), f"gacha_record_{token_hex(16)}.jpg")
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed:
                return await ctx.scene.send_message(picture(url, ctx))
    except RuntimeError as e:
        return await ctx.scene.send_message(str(e))


@alcommand(alc)
@assign("更新")
@record("抽卡查询")
# @exclusive
@accessable
async def update(ctx: Context, arp: Arparma):
    if not arp.other_args.get("name"):
        await generate(Path(f"{bot.config.plugin_data_dir / 'recordpool.json'}").absolute(), proxy=bot.config.proxy)
    else:
        with open(f"{bot.config.plugin_data_dir / 'recordpool.json'}", encoding="utf-8") as f:
            pool = json.load(f)
        pool[arp.name] = {"is_exclusive": arp.limit}
    update_operators()
    return await ctx.scene.send_message("更新完成")


@alcommand(alc)
@assign("绑定")
@record("抽卡查询")
# @exclusive
@accessable
async def bind(ctx: Context, token: Match[str]):
    if "content" in token.result:
        token.result = re.match('.*content(")?:(")?(?P<token>[^{}"]+).*', token.result)["token"]
    try:
        res = querier.user_token_save(token.result, f"{ctx.client.last_value}")
    except RuntimeError as e:
        return await ctx.scene.send_message(str(e))
    return await ctx.scene.send_message(res)
