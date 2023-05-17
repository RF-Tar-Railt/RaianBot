import asyncio
from library.queryop import handle
from arclet.alconna import Alconna, Args, Arparma, Field, CommandMeta
from arclet.alconna.graia import alcommand, Match
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Source
from graia.ariadne.app import Ariadne
from graiax.playwright import PlaywrightBrowser
from playwright.async_api import Page, TimeoutError
from app import Sender, RaianBotService, accessable, exclusive, record
from pathlib import Path
from hashlib import md5
from contextlib import suppress

bot = RaianBotService.current()
cache = Path(f"{bot.config.plugin_cache_dir / 'op_query'}")
cache.mkdir(parents=True, exist_ok=True)
running = asyncio.Event()




@alcommand(
    Alconna(
        "干员{operator}?",
        Args["content", str, Field("干员信息", completion=lambda: ["档案", "精英化材料", "技能升级材料", "属性"])],
        meta=CommandMeta("查询干员信息", usage="大致按照prts的分区板块来查询", example="$干员艾雅法拉 档案"),
    )
)
@record("干员查询")
@exclusive
@accessable
async def weather(app: Ariadne, sender: Sender, content: Match[str], result: Arparma, source: Source):
    name = result.header["operator"] or "艾雅法拉"
    if running.is_set():
        return await app.send_message(sender, "请耐心排队~")
    browser: PlaywrightBrowser = app.launch_manager.get_interface(PlaywrightBrowser)
    async with browser.page(viewport={'width': 1920, 'height': 1080}) as page:
        page: Page
        hs = md5((name + content.result).encode()).hexdigest()
        if (path := (cache / f"{hs}.png")).exists():
            with path.open("rb") as f:
                data = f.read()
        else:
            with suppress(TimeoutError):
                await page.goto(f"https://prts.wiki/index.php?title={name}&action=edit")
                if await page.locator("text=需要登录").count():
                    return await app.send_message(sender, MessageChain("不对劲。。。"))
            try:
                running.set()
                func = handle(content.result)
                data = await func(page, name)
                with path.open("wb+") as f:
                    f.write(data)
            except TimeoutError:
                return await app.send_message(sender, MessageChain("prts超时，请重试！"))
            finally:
                running.clear()
    return await app.send_message(sender, MessageChain(Image(data_bytes=data)), quote=source)
