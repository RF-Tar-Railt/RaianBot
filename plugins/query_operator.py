from typing import Optional

from arknights_toolkit.info import *
from arclet.alconna import Args, Arpamar, ArgField, CommandMeta
from arclet.alconna.graia import Alconna, alcommand, Match
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Source
from graia.ariadne.app import Ariadne
from graiax.playwright import PlaywrightBrowser
from playwright.async_api import Page, TimeoutError
from app import Sender, RaianMain
from pathlib import Path
from hashlib import md5
from functools import partial
import re
from contextlib import suppress

bot = RaianMain.current()
cache = Path(f"{bot.config.cache_dir}/plugins/op_query")
cache.mkdir(parents=True, exist_ok=True)

_table = {
    "总览": full_page,
    "((干员)?信息|展示)": information,
    "(模板|职业)?特性": feature,
    "属性": attributes,
    "攻击范围": attack_range,
    "天赋": talent,
    "潜能(提升)?": latent,
    "技能(信息)?": skills,
    "后勤技能": logistics,
    "精二": partial(information, upgraded=True),
    "精英化(材料)?": upgrade,
    "技能升级材料": material,
    "(.*?)专(一|二|三|精)(材料)?": material,
    "档案": document
}


def _handle(content: Optional[str] = None):
    if not content:
        return full_page
    for pat, func in _table.items():
        if re.fullmatch(pat, content):
            return func
    return full_page


@alcommand(
    Alconna(
        "干员{operator}?",
        Args["content", str, ArgField("干员信息", completion=lambda: ["档案", "精英化材料", "技能升级材料", "属性"])],
        meta=CommandMeta("查询干员信息", usage="大致按照prts的分区板块来查询", example="$干员艾雅法拉 档案"),
    )
)
async def weather(app: Ariadne, sender: Sender, content: Match[str], result: Arpamar, source: Source):
    name = result.header["operator"] or "艾雅法拉"
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
                func = _handle(content.result)
                data = await func(page, name)
                with path.open("wb+") as f:
                    f.write(data)
            except TimeoutError:
                return await app.send_message(sender, MessageChain("prts超时，请重试！"))

    return await app.send_message(sender, MessageChain(Image(data_bytes=data)), quote=source)
