from io import BytesIO
from secrets import token_hex

from arclet.alconna import Alconna, CommandMeta
from arclet.alconna.graia import alcommand
from avilla.core import Context, RawResource
from avilla.core.elements import Picture
from avilla.qqapi.exception import ActionFailed
from graia.amnesia.builtins.aiohttp import AiohttpClientService
from PIL import Image as Img

from app.core import RaianBotService
from app.shortcut import accessable, exclusive, picture, record

cmd = Alconna(
    "结婚",
    meta=CommandMeta("结婚", extra={"supports": {"mirai", "qqapi"}}),
)


@alcommand(cmd, post=True, send_error=True)
@record("marry")
@exclusive
@accessable
async def marry(ctx: Context, aio: AiohttpClientService, bot: RaianBotService):
    try:
        avatar = await ctx.client.avatar()
    except NotImplementedError:
        return await ctx.scene.send_message("该平台不支持获取头像")
    cover = Img.open("assets/image/marry.png")
    async with aio.session.get(avatar.url) as resp:
        base = Img.open(BytesIO(await resp.content.read())).resize(cover.size, Img.Resampling.LANCZOS)
    cover.thumbnail(cover.size)
    base.paste(cover, (0, 0), cover)
    data = BytesIO()
    base.save(data, format="PNG", quality=90, qtables="web_high")
    try:
        return await ctx.scene.send_message(Picture(RawResource(data.getvalue())))
    except Exception:
        url = await bot.upload_to_cos(data.getvalue(), f"marry_{token_hex(16)}.png")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed as e:
            return await ctx.scene.send_message(f"图片发送失败:\ncode: {e.code}\nmsg: {e.message}")
