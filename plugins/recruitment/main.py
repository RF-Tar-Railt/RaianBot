from secrets import token_hex

from arclet.alconna import Alconna, Args, CommandMeta, Field, MultiVar
from arclet.alconna.graia import Match, alcommand
from arknights_toolkit.recruit import recruitment
from avilla.core import Context, Picture, RawResource
from avilla.elizabeth.account import ElizabethAccount
from graiax.playwright import PlaywrightBrowser, PlaywrightService

from app.core import RaianBotService
from app.shortcut import accessable, picture

recruit = Alconna(
    "公招",
    Args["tags", MultiVar(str, "*"), Field(completion=lambda: "高资")],
    meta=CommandMeta("自助访问 prts 的公招计算器并截图", usage="标签之间用空格分隔", example="$公招 高资 生存"),
)


@alcommand(recruit, send_error=True, post=True)
# @exclusive
@accessable
async def recruit(ctx: Context, tags: Match[tuple[str, ...]], pw: PlaywrightService, bot: RaianBotService):
    if not tags.available or not tags.result:
        return await ctx.scene.send_message("缺失标签")
    await ctx.scene.send_message("正在获取中，请稍等。。。")
    # Click html
    browser: PlaywrightBrowser = pw.get_interface(PlaywrightBrowser)
    # Go to https://prts.wiki/w/%E5%B9%B2%E5%91%98%E4%B8%80%E8%A7%88
    url = recruitment([x.replace("干员", "").replace("高级资深", "高级资深干员") for x in tags.result])
    page = await browser.new_page()
    try:
        await page.goto(url, timeout=60000, wait_until="networkidle")  # type: ignore
        locator = page.locator('//div[@id="root"]')
        elem = locator.first.locator("//table[1]").nth(1)
        await elem.click()
        await page.wait_for_timeout(1000)
        data = await page.screenshot(type="png", clip=await elem.bounding_box())
        try:
            return await ctx.scene.send_message(Picture(RawResource(data)))
        except Exception:
            url = await bot.upload_to_cos(data, f"recruit_{token_hex(16)}.png")
            return await ctx.scene.send_message(picture(url, ctx))
    except Exception:
        await ctx.scene.send_message("prts超时，获取失败")
        if isinstance(ctx.account, ElizabethAccount):
            await ctx.scene.send_message(url)
    finally:
        await page.close()
