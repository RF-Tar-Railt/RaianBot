from typing import Union
from playwright.async_api import async_playwright
from arclet.alconna import Args
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Source
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from config import bot_config

channel = Channel.current()

random_ope = Alconna(
    "公招", Args["tags;S":str:...],
    headers=bot_config.command_prefix,
    help_text="自助访问 prts 的公招计算器并截图 Usage: 标签之间用空格分隔; Example: .公招 高资 生存;",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=random_ope, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def recruitment(app: Ariadne, sender: Union[Group, Friend], source: Source, result: AlconnaProperty):
    arp = result.result
    if arp.tags is None:
        return await app.sendMessage(sender, MessageChain.create('不对劲...'))
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
            for tag in arp.tags:
                tag = tag.replace("术士", "术师").replace("高资", "高级资深干员")
                if tag != "":
                    await page.click("text=" + tag)
            # ---------------------
            data = await page.screenshot(full_page=True, omit_background=True)
            await context.close()
            await browser.close()
            await app.sendMessage(sender, MessageChain.create(Image(data_bytes=data)), quote=source.id)
        except Exception:
            await app.sendMessage(sender, MessageChain.create('prts超时，获取失败'), quote=source.id)
