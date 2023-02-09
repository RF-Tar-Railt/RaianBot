import re
import time
import aiohttp
import asyncio

import contextlib
import pypinyin
from playwright.async_api import TimeoutError, Page
from app import Sender, exclusive, accessable, record
from arclet.alconna import Alconna, Args, CommandMeta
from arclet.alconna.graia import alcommand, Match
from graia.ariadne.app import Ariadne
from graiax.playwright import PlaywrightBrowser
from graia.ariadne.event.lifecycle import AccountLaunch
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source, Image
from graia.ariadne.util.cooldown import CoolDown
from graiax.shortcut.saya import dispatch, listen


characters = {}
sem = asyncio.Semaphore(1)
running = asyncio.Event()
cmd = Alconna(
    "原神角色卡",
    Args["uid;/", "[12][0-9]{8}"]["name", str],
    meta=CommandMeta("原神角色卡查询")
)

@listen(AccountLaunch)
async def init():
    global characters
    if not characters:
        characters = await init_chara_list()
        print(characters)

@alcommand(cmd, send_error=True)
@record("原神角色卡查询")
@exclusive
@accessable
async def genshin_chara_card(app: Ariadne, sender: Sender, source: Source, uid: Match[str], name: Match[str]):
    global characters
    if running.is_set():
        return await app.send_message(sender, "请耐心排队~")
    running.set()
    start_time = time.time()
    uid = uid.result
    chara = name.result.strip()
    chara_pinyin = "".join(pypinyin.lazy_pinyin(chara))
    if not characters:
        characters = await init_chara_list()
    if chara_pinyin not in characters:
        return await app.send_message(sender, MessageChain(f"角色列表中未找到角色：{chara}，请检查拼写"))
    url = f"https://enka.shinshin.moe/u/{uid}"
    browser = app.launch_manager.get_interface(PlaywrightBrowser)
    try:
        async with browser.page() as page:
            page: Page
            await page.goto(url, wait_until="networkidle", timeout=100000)
            await page.set_viewport_size({"width": 2560, "height": 1080})
            await page.evaluate(
                "document.getElementsByClassName('Dropdown-list')[0].children[13].dispatchEvent(new Event('click'));"
            )
            clen = await page.locator(".chara").count()
            styles = [(await page.locator(".chara").nth(i).get_attribute("style")) for i in range(clen)]
            if all(characters[chara_pinyin] not in style.lower() for style in styles):
                return await app.send_message(
                    sender,
                    MessageChain(
                        f"未找到角色{chara} | {chara_pinyin}！只查询到这几个呢（只能查到展柜里有的呢）："
                        f"{'、'.join([k for k, v in characters.items() if any(v in style.lower() for style in styles)])}"
                    ),
                    quote=source,
                )
            index = -1
            chara_src = ""
            for i, style in enumerate(styles):
                if characters[chara_pinyin] in style.lower():
                    index = i
                    chara_src = style
                    break
            if index == -1 or not chara_src:
                return await app.send_message(sender, MessageChain("获取角色头像div失败！"))

            await page.locator(f"div.avatar.svelte-jlfv30 >> nth={index}").click()
            await asyncio.sleep(1)
            await page.get_by_role("button", name=re.compile("Export image", re.IGNORECASE)).click()
            async with page.expect_download() as download_info:
                for _ in range(3):
                    with contextlib.suppress(TimeoutError):
                        await page.get_by_role("button", name=re.compile("Download", re.IGNORECASE)).click(timeout=10000)
            path = await (await download_info.value).path()
            await app.send_message(
                sender,
                MessageChain(
                    f"use: {round(time.time() - start_time, 2)}s\n",
                    Image(path=path)
                ),
                quote=source,
            )
    finally:
        running.clear()

async def init_chara_list():
    res = {}
    url = "https://genshin.honeyhunterworld.com/fam_chars/?lang=CHS"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
    datas = re.findall(r"sortable_data.push\(\[(.*?)]\)", html, re.S)
    data = datas[0].replace(r"\"", '"').replace(r"\\", "\\").replace(r"\/", "/")
    cs = data[1:-1].split("],[")
    for c in cs:
        chn_name = re.findall(r'<img loading="lazy" alt="(.+?)"', c, re.S)[0]
        chn_name = chn_name.encode().decode("unicode_escape")
        en_name = re.findall(r'<a href="/(.+?)_.+/?lang=CHS"', c, re.S)[0]
        res["".join(pypinyin.lazy_pinyin(chn_name))] = en_name.lower()
    return res