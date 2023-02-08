import random

from app import Sender, Target, accessable, exclusive, record
from arclet.alconna import Args, Empty
from arclet.alconna.graia import alc, fetch_name, Query
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image
from graiax.playwright import PlaywrightBrowser
from graiax.shortcut.saya import decorate, listen


@listen(GroupMessage, FriendMessage)
@alc.command("地下城抽签")
@alc.argument("name", [str, At], Empty)
@alc.option("年龄", Args["age", int])
@alc.option("地址", Args["loc", str])
@alc.option("电话", Args["phone", int])
@alc.help("测试您在流浪地球计划下的地下城资格", example="$地下城抽签 仙贝 地址 东京湾")
@decorate({"name": fetch_name()})
@record("地下城抽签")
@exclusive
@accessable
async def dndraw(
    app: Ariadne,
    sender: Sender,
    target: Target,
    name: str,
    age: Query[int] = Query('年龄.age', 18),
    loc: Query[str] = Query('地址.loc', '下北泽'),
    phone: Query[int] = Query('电话.phone', 11451419198)
):
    """测试您在流浪地球计划下的地下城资格"""
    profile = await app.get_user_profile(target)
    gender = {"MALE": 0, "FEMALE": 1, "UNKNOWN": random.randint(0, 1)}
    browser: PlaywrightBrowser = app.launch_manager.get_interface(PlaywrightBrowser)
    async with browser.page() as page:
        await page.click("html")
        await page.goto(
            f"https://uegov.world/random-draw/gen.html"
            f"?name={name or profile.nickname}"
            f"&age={profile.age or age.result}"
            f"&loc={loc.result}"
            f"&gender={gender[profile.sex]}"
            f"&phone={phone.result}"
        )
        img = page.locator("//img[@alt='uegov.world']")
        await img.nth(1).evaluate("node => node.remove()")
        elem = page.locator("//div[@class='nav row items-center space-between']")
        elem1 = page.locator("//main[@id='main']")
        bounding = await elem.bounding_box()
        bounding1 = await elem1.bounding_box()
        bounding["x"] += 10
        bounding["width"] -= 10
        bounding["height"] += bounding1["height"]
        res = MessageChain(Image(data_bytes=await page.screenshot(full_page=True, clip=bounding)))
    return await app.send_message(sender, res)
