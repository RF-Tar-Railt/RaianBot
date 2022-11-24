from io import BytesIO

from arclet.alconna.graia import alcommand, Match
from arclet.alconna import Alconna, CommandMeta, Args, ArgField
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.app import Ariadne
from graiax.playwright import PlaywrightBrowser
from playwright.async_api import Page, ConsoleMessage
from graia.ariadne.util.interrupt import FunctionWaiter
from app import Sender, record
from asyncio import Event
from PIL import Image as PILImage, ImageDraw, ImageFont

cmd_go = Alconna(
    "五子棋",
    Args["first", {"我先": True, "电脑先": False}, ArgField(True, alias="我先")],
    Args["rand", {"随机开局": True}, ArgField(False, alias="否")],
    meta=CommandMeta("人机五子棋游戏"),
)

running = Event()


@alcommand(cmd_go, private=False)
@record("五子棋")
async def gobang(app: Ariadne, sender: Sender, first: Match[bool], rand: Match[bool]):
    if running.is_set():
        return await app.send_message(sender, "请耐心排队~")
    start = Event()
    browser: PlaywrightBrowser = app.launch_manager.get_interface(PlaywrightBrowser)
    async with browser.page() as page:
        page: Page
        over = False

        async def callback(msg: ConsoleMessage):
            nonlocal over, start
            if msg.type == "log":
                for args in msg.args:
                    value = await args.json_value()
                    if isinstance(value, dict) and value["type"] == "START":
                        start.set()
                    if isinstance(value, str) and value == "is five":
                        over = True

        async def waiter(w_sender: Sender, message: MessageChain):
            if w_sender.id == sender.id:
                msg = str(message)
                if msg in {"取消", "认输", "结束游戏", "游戏结束"}:
                    return False
                if msg.isalpha() and len(msg) > 1:
                    return ord(msg[0].upper()) - 65, ord(msg[1].upper()) - 65

        running.set()

        await page.click("html")
        page.on("console", callback)
        await page.goto("http://gobang.light7.cn/#/")
        if rand.result:
            await page.get_by_role("link", name=" 设置").click()
            await page.get_by_role("checkbox").nth(1).check()
            await page.get_by_role("link", name=" 首页").click()
        await page.get_by_role("link", name="开始").click()
        bio = BytesIO()
        if first.result:
            await page.get_by_role("link", name="我").click()  # 电脑
        else:
            await page.get_by_role("link", name="电脑").click()  # 电脑
        await start.wait()
        lct = page.locator(".board-inner")
        state = page.locator("//div[@class='status-inner']")
        img: PILImage.Image = PILImage.open(BytesIO(await lct.screenshot()))
        draw = ImageDraw.Draw(img)
        new_font = ImageFont.truetype("simkai.ttf", 18)  # 52

        for i in range(15):
            draw.text((500, 28 + i * 34 - 18), text=chr(65 + i), fill="red", font=new_font)
            draw.text((28 + i * 34 - 11, 2), text=chr(65 + i), fill="red", font=new_font)

        img.save(
            bio,
            format="PNG",
            quality=90,
            subsampling=2,
            qtables="web_high",
        )
        await app.send_message(sender, MessageChain(Image(data_bytes=bio.getvalue())))
        await app.send_message(sender, "五子棋游戏开始！\n发送 取消 可以结束当前游戏\n发送坐标来下子，例如“HH”")
        while (await state.inner_text()) != " 请点击 `开始` 按钮":
            _bio = BytesIO()
            res = await FunctionWaiter(waiter, [GroupMessage]).wait(timeout=120, default=False)
            if res is None:
                continue
            if res is False:
                break
            px, py = res
            if px > 14 or py > 14:
                continue
            await page.locator(".board-inner").click(position={"x": 22 + px * 35, "y": 22 + py * 35})
            if await (node := page.locator(".popover")).count():
                await node.first.evaluate("node => node.remove()")
            while not (await state.inner_text()).startswith(" 分数"):
                await page.wait_for_timeout(100)
            img: PILImage.Image = PILImage.open(BytesIO(await lct.screenshot(animations="disabled")))
            draw = ImageDraw.Draw(img)
            new_font = ImageFont.truetype("simkai.ttf", 18)  # 52

            for i in range(15):
                draw.text((500, 28 + i * 34 - 18), text=chr(97 + i), fill="red", font=new_font)
                draw.text((28 + i * 34 - 11, 2), text=chr(65 + i), fill="red", font=new_font)

            img.save(
                _bio,
                format="PNG",
                quality=90,
                subsampling=2,
                qtables="web_high",
            )
            await app.send_message(sender, MessageChain(Image(data_bytes=_bio.getvalue())))
        running.clear()
        return await app.send_message(sender, "五子棋游戏结束！")
