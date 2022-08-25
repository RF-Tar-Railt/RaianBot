from typing import AsyncContextManager
from playwright.async_api import async_playwright, Page, BrowserContext, Browser, Playwright
from arclet.alconna import Args, Arpamar, Option, ArgField, CommandMeta
from arclet.alconna.graia import Alconna, command
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Source
from graia.ariadne.app import Ariadne
from graia.ariadne.event.lifecycle import ApplicationShutdowned, ApplicationLaunch
from graia.ariadne.util.saya import listen
from loguru import logger

from app import Sender
from modules.arknights.recruiment import recruitment

recruit = Alconna(
    "公招", Args["tags;S", str, ArgField(..., completion=lambda x: "高资")],
    options=[Option("详细|--d", dest='detail')],
    meta=CommandMeta("自助访问 prts 的公招计算器并截图", usage="标签之间用空格分隔", example="$公招 高资 生存")
)


class PlaywrightMounter:
    playwright_mgr: AsyncContextManager[Playwright]
    browser: Browser
    context: BrowserContext
    page: Page


@listen(ApplicationLaunch)
async def init_playwright():
    PlaywrightMounter.playwright_mgr = async_playwright()
    playwright = await PlaywrightMounter.playwright_mgr.__aenter__()
    PlaywrightMounter.browser = await playwright.chromium.launch(headless=True)
    PlaywrightMounter.context = await PlaywrightMounter.browser.new_context()
    # Open new page
    PlaywrightMounter.page = await PlaywrightMounter.context.new_page()
    logger.debug("[recruitment] playwright 初始化完成")


@listen(ApplicationShutdowned)
async def del_playwright():
    await PlaywrightMounter.page.close()
    await PlaywrightMounter.browser.close()
    await PlaywrightMounter.playwright_mgr.__aexit__(None, None, None)
    logger.debug("[recruitment] playwright 已关闭")


@command(recruit, send_error=True)
async def recruit(app: Ariadne, sender: Sender, source: Source, result: Arpamar):
    if result.tags is None:
        return await app.send_message(sender, MessageChain('不对劲...'))
    await app.send_message(sender, MessageChain('正在获取，请稍等。。。'), quote=source.id)
    # Click html
    await PlaywrightMounter.page.click("html")
    # Go to https://prts.wiki/w/%E5%B9%B2%E5%91%98%E4%B8%80%E8%A7%88
    url = recruitment(
        list(map(lambda x: x.replace("干员", "").replace("高级资深", "高级资深干员"), result.tags)),
        not result.find('detail')
    )
    try:
        await PlaywrightMounter.page.goto(
            url, timeout=60000,
            wait_until='networkidle' if result.find('detail') else 'load'  # type: ignore
        )
        elem = await PlaywrightMounter.page.query_selector("table#calc-result")
        bounding = await elem.bounding_box()
        data = await PlaywrightMounter.page.screenshot(full_page=True, clip=bounding)
        await app.send_message(sender, MessageChain(Image(data_bytes=data)))
    except Exception:
        await app.send_message(sender, MessageChain('prts超时，获取失败'), quote=source.id)
        await app.send_message(sender, MessageChain(url), quote=source.id)
