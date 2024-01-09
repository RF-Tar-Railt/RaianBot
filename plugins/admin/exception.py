import traceback
from contextlib import suppress
from io import StringIO

from arclet.alconna.graia import startswith
from avilla.core import Avilla, Context, Picture, RawResource
from avilla.elizabeth.account import ElizabethAccount
from avilla.standard.core.message import MessageReceived
from avilla.standard.core.profile import NickCapability
from graia.broadcast.builtin.event import ExceptionThrown
from graia.saya.builtins.broadcast.shortcut import listen, priority

from app.config import BotConfig
from app.core import RaianBotService
from app.image import md2img
from app.shortcut import allow, exclusive, permission
from library.tencentcloud import TencentCloudApi

bot = RaianBotService.current()

api = None
if bot.config.platform.tencentcloud_secret_id:
    api = TencentCloudApi(
        bot.config.platform.tencentcloud_secret_id,
        bot.config.platform.tencentcloud_secret_key,
        proxy=bot.config.proxy,
    )


@listen(MessageReceived)
@permission("admin")
@allow(ElizabethAccount)
@startswith("昵称还原")
@exclusive
async def nickname_restore(ctx: Context, conf: BotConfig):
    for gid in bot.cache.get("$name_change", []):
        await ctx[NickCapability.set_nickname](gid.member(ctx.account.route["account"]), conf.name)
    bot.cache.pop("$name_change", None)
    await ctx.scene.send_message("已完成")


@listen(ExceptionThrown)
@priority(13)
async def report(event: ExceptionThrown, avilla: Avilla):
    with StringIO() as fp:
        traceback.print_tb(event.exception.__traceback__, file=fp)
        tb = fp.getvalue()
    data = {
        "event": str(event.event.__repr__()),
        "exctype": str(type(event.exception)),
        "exc": str(event.exception),
        "traceback": tb,
    }
    masters = {conf.master_id for conf in bot.config.bots}
    if api:
        masters = {f"{conf.master_id}@qq.com" for conf in bot.config.bots}
        with suppress(Exception):
            await api.send_email(
                "notice@dunnoaskrf.top",
                [f"{master}@qq.com" for master in masters],
                "Exception Occur",
                27228,
                data,
            )
    template = """\
## 异常事件：

`{event}`

## 异常类型：

`{exctype}`

## 异常内容：

{exc}

## 异常追踪：

```py
{traceback}
```
"""
    img = await md2img(template.format_map(data), 1500)
    if not (accounts := avilla.get_accounts(account_type=ElizabethAccount)):
        return
    for account in accounts:
        async for friend in account.account.staff.query_entities("land.friend", friend=lambda x: x in masters):
            ctx = account.account.get_context(friend)
            await ctx.scene.send_message(Picture(RawResource(img)))
