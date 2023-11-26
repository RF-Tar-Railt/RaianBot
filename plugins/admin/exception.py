import traceback
from contextlib import suppress
from io import StringIO

from arclet.alconna.graia import startswith
from avilla.core import Avilla, Context, Picture, RawResource
from avilla.core.exceptions import AccountMuted
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
    if isinstance(event.exception, AccountMuted) and isinstance(event.event, MessageReceived):
        # for listener in app.broadcast.default_listener_generator(AccountMutedEvent):
        #     await listener.callable(app, event.event.sender.group, interface)
        # return
        ...
    with StringIO() as fp:
        traceback.print_tb(event.exception.__traceback__, file=fp)
        tb = fp.getvalue()
    msg = f"""\
## 异常事件：

`{str(event.event.__repr__())}`

## 异常类型：

`{type(event.exception)}`

## 异常内容：

{str(event.exception)}

## 异常追踪：

```py
{tb}
```
"""
    masters = {conf.master_id for conf in bot.config.bots}
    if api:
        masters = {f"{conf.master_id}@qq.com" for conf in bot.config.bots}
        with suppress(Exception):
            await api.send_email(
                "notice@dunnoaskrf.top",
                [f"{master}@qq.com" for master in masters],
                "Exception Occur",
                "27228",
                {
                    "event": str(event.event.__repr__()),
                    "exctype": str(type(event.exception)),
                    "exc": str(event.exception),
                    "traceback": tb,
                },
            )
    img = await md2img(msg, 1500)
    if not (accounts := avilla.get_accounts(account_type=ElizabethAccount)):
        return
    for account in accounts:
        async for friend in account.account.staff.query_entities("land.friend", friend=lambda x: x in masters):
            ctx = account.account.get_context(friend)
            await ctx.scene.send_message(Picture(RawResource(img)))
