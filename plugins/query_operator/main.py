import asyncio
from hashlib import md5
from pathlib import Path
from secrets import token_hex

import ujson
from arclet.alconna import Alconna, Args, CommandMeta, Field
from arclet.alconna.graia import Match, alcommand
from arknights_toolkit.update import main
from avilla.core import Context, Picture, RawResource
from graiax.playwright import PlaywrightBrowser, PlaywrightService
from playwright.async_api import Page, TimeoutError as PwTimeoutError

from app.core import RaianBotService
from app.shortcut import accessable, picture, record
from library.queryop import handle

bot = RaianBotService.current()
cache = Path(f"{bot.config.plugin_data_dir / 'op_query'}")
cache.mkdir(parents=True, exist_ok=True)
running = asyncio.Event()


alc = Alconna(
    "查询干员",
    Args["name", str],
    Args[
        "content",
        str,
        Field("干员信息", completion=lambda: ["档案", "精英化材料", "技能升级材料", "属性"]),
    ],
    meta=CommandMeta(
        "查询干员信息",
        usage="大致按照prts的分区板块来查询",
        example="$查询干员 艾雅法拉 档案\n$干员艾雅法拉 档案",
    ),
)
alc.shortcut(
    "干员(?P<name>.+)",
    command="查询干员 {name} {*}",
    prefix=True,
)


@alcommand(alc, post=True, send_error=True)
@record("干员查询")
# @exclusive
@accessable
async def query(ctx: Context, name: Match[str], content: Match[str], pw: PlaywrightService):
    if running.is_set():
        return await ctx.scene.send_message("请耐心排队~")
    browser: PlaywrightBrowser = pw.get_interface(PlaywrightBrowser)
    async with browser.page(viewport={"width": 1920, "height": 1080}) as page:
        page: Page
        hs = md5((name.result + content.result).encode()).hexdigest()
        if (path := (cache / f"{hs}.png")).exists():
            with path.open("rb") as f:
                data = f.read()
        else:
            with main.info_path.absolute().open("r+", encoding="utf-8") as _f:
                _infos = ujson.load(_f)
            if name.result not in _infos["tables"]:
                return await ctx.scene.send_message("不对劲。。。")
            try:
                running.set()
                func = handle(content.result)
                data = await func(page, name)
                with path.open("wb+") as f:
                    f.write(data)
            except (PwTimeoutError, TimeoutError):
                return await ctx.scene.send_message("prts超时，请重试！")
            finally:
                running.clear()
    try:
        return await ctx.scene.send_message(Picture(RawResource(data)))
    except Exception:
        url = await bot.upload_to_cos(data, f"query_op_{token_hex(16)}.png")
        return await ctx.scene.send_message(picture(url, ctx))
