from secrets import token_hex
from typing import Union

from arclet.alconna import Alconna, Args, Arparma, CommandMeta
from arclet.alconna.graia import alcommand
from avilla.core import Context, RawResource
from avilla.core.elements import Notice, Picture
from avilla.elizabeth.account import ElizabethAccount
from avilla.qqapi.exception import ActionFailed
from avilla.standard.core.activity import ActivityTrigged
from graia.amnesia.builtins.aiohttp import AiohttpClientService
from graia.saya.builtins.broadcast.shortcut import listen

from app.core import RaianBotService
from app.shortcut import accessable, allow, exclusive, picture, record
from library.petpet import generate

rua = Alconna(
    "摸",
    Args["target", [Notice, int]],
    meta=CommandMeta("rua别人", example="$摸@123456", extra={"supports": {"mirai"}}),
)


@alcommand(rua, post=True, send_error=True)
@record("rua")
@allow(ElizabethAccount)
@exclusive
@accessable
async def rua(
    ctx: Context,
    arp: Arparma,
    bot: RaianBotService,
    aio: AiohttpClientService,
):
    target = arp.query[Union[Notice, int]]("target")
    target_id = target if isinstance(target, int) else int(target.target.pattern["member"])
    async with aio.session.get(f"https://q1.qlogo.cn/g?b=qq&nk={target_id}&s=640") as resp:
        data = await resp.read()
    img = generate(data).getvalue()
    # await app.send_nudge(member, sender)
    try:
        return await ctx.scene.send_message(Picture(RawResource(img)))
    except Exception:
        url = await bot.upload_to_cos(img, f"rua_{token_hex(16)}.jpg")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed as e:
            return await ctx.scene.send_message(f"图片发送失败:\ncode: {e.code}\nmsg: {e.message}")


@listen(ActivityTrigged)
@record("rua")
@accessable
async def nudge(event: ActivityTrigged, aio: AiohttpClientService, bot: RaianBotService):
    if event.id != "nudge":
        return
    if event.context.endpoint.last_value != event.context.account.route["account"]:
        return
    async with aio.session.get(f"https://q1.qlogo.cn/g?b=qq&nk={event.trigger.last_value}&s=640") as resp:
        data = await resp.read()
    img = generate(data)
    try:
        return await event.context.scene.send_message(Picture(RawResource(img.getvalue())))
    except Exception:
        url = await bot.upload_to_cos(img.getvalue(), f"rua_{token_hex(16)}.jpg")
        try:
            return await event.context.scene.send_message(picture(url, event.context))
        except ActionFailed as e:
            return await event.context.scene.send_message(f"图片发送失败:\ncode: {e.code}\nmsg: {e.message}")
