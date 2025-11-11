from io import BytesIO
from secrets import token_hex

from arclet.alconna import Alconna, CommandMeta
from arclet.alconna.avilla import alcommand, assign
from arknights_toolkit.copper import draw_copper
from avilla.core import Context, MessageChain, Picture, RawResource

from app.core import RaianBotService
from app.shortcut import accessable, exclusive, picture, record


bot = RaianBotService.current()
cmd = Alconna(
    "投钱",
    meta=CommandMeta("模拟界园投钱", example="$投钱", extra={"supports": {"mirai", "qqapi"}}),
)


@alcommand(cmd, send_error=True, post=True)
@assign("$main")
@record("投钱")
@exclusive
@accessable
async def draw_cop_(ctx: Context):
    """模拟界园投钱"""

    img = draw_copper()
    imageio = BytesIO()
    img.save(
        imageio,
        format="JPEG",
        quality=95,
        subsampling=2,
        qtables="web_high",
    )
    data = imageio.getvalue()
    try:
        return await ctx.scene.send_message(MessageChain([Picture(RawResource(data))]))
    except Exception:
        url = await bot.upload_to_cos(data, f"copper_{token_hex(16)}.png")
        return await ctx.scene.send_message(picture(url, ctx))
