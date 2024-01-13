from secrets import token_hex

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Field, MultiVar
from arclet.alconna.graia import alcommand
from arknights_toolkit.recruit import recruitment
from avilla.core import Context, Picture, RawResource
from avilla.elizabeth.account import ElizabethAccount
from avilla.qqapi.exception import ActionFailed
from graiax.playwright import PlaywrightBrowser, PlaywrightService

from app.core import RaianBotService
from app.shortcut import accessable, exclusive, picture

cmd = Alconna(
    "公招",
    Args[
        "tags",
        MultiVar(str, "*"),
        Field(completion=lambda: "高资", unmatch_tips=lambda x: f"输入的应该是公招标签，而不是{x}\n例如：/公招 高资"),
    ],
    meta=CommandMeta(
        "自助访问 prts 的公招计算器并截图",
        usage="标签之间用空格分隔",
        example="$公招 高资 生存",
        extra={"supports": {"mirai", "qqapi"}},
    ),
)


@alcommand(cmd, send_error=True, post=True)
@exclusive
@accessable
async def recruit(ctx: Context, res: Arparma, pw: PlaywrightService, bot: RaianBotService):
    if not res.all_matched_args.get("tags"):
        return await ctx.scene.send_message("缺失标签\n试试比如 /公招 高资")
    tags: tuple[str, ...] = res.all_matched_args["tags"]
    await ctx.scene.send_message("正在获取中，请稍等。。。")
    # Click html
    browser: PlaywrightBrowser = pw.get_interface(PlaywrightBrowser)
    # Go to https://prts.wiki/w/%E5%B9%B2%E5%91%98%E4%B8%80%E8%A7%88
    url = recruitment([x.replace("干员", "").replace("高级资深", "高级资深干员") for x in tags])
    page = await browser.new_page(viewport={"width": 1200, "height": 2400})
    try:
        await page.goto(url, timeout=60000, wait_until="networkidle")  # type: ignore
        locator = page.locator('//div[@id="root"]')
        elem = locator.first.get_by_role("table").nth(1)
        # await elem.click()
        await page.wait_for_timeout(1000)
        data = await page.screenshot(type="png", clip=await elem.bounding_box())
        try:
            return await ctx.scene.send_message(Picture(RawResource(data)))
        except Exception:
            url = await bot.upload_to_cos(data, f"recruit_{token_hex(16)}.png")
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed as e:
                return await ctx.scene.send_message(f"图片发送失败:\ncode: {e.code}\nmsg: {e.message}")
    except Exception:
        await ctx.scene.send_message("prts超时，获取失败")
        if isinstance(ctx.account, ElizabethAccount):
            await ctx.scene.send_message(url)
    finally:
        await page.close()
