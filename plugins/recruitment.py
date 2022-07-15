from playwright.async_api import async_playwright
from arclet.alconna import Args, Arpamar
from arclet.alconna.graia import Alconna, command
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Source
from graia.ariadne.app import Ariadne

from app import Sender

recruit = Alconna(
    "公招", Args["tags;S", str, ...],
    help_text="自助访问 prts 的公招计算器并截图 Usage: 标签之间用空格分隔; Example: $公招 高资 生存;",
)


@command(recruit, send_error=True)
async def recruitment(app: Ariadne, sender: Sender, source: Source, result: Arpamar):
    if result.tags is None:
        return await app.send_message(sender, MessageChain('不对劲...'))
    await app.send_message(sender, MessageChain('正在获取，请稍等。。。'), quote=source.id)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        # Open new page
        page = await context.new_page()
        # Click html
        await page.click("html")
        # Go to https://prts.wiki/w/%E5%B9%B2%E5%91%98%E4%B8%80%E8%A7%88
        try:
            await page.goto("https://prts.wiki/w/%E5%B9%B2%E5%91%98%E4%B8%80%E8%A7%88", timeout=60000)
            await page.click("text=极简模式")
            # Click text=公开招募计算
            await page.click("text=公开招募计算")
            for tag in result.tags:
                tag = tag.replace("术士", "术师").replace("干员", "").replace(
                    "资深", "资深干员").replace("高级资深", "高级资深干员").replace("高资", "高级资深干员")
                if tag != "":
                    await page.click(f"text={tag}")
            # ---------------------
            data = await page.screenshot(full_page=True, omit_background=True)
            await context.close()
            await browser.close()
            await app.send_message(sender, MessageChain(Image(data_bytes=data)))
        except Exception:
            await app.send_message(sender, MessageChain('prts超时，获取失败'), quote=source.id)
