from datetime import datetime
from arclet.alconna import Args, Option, ArgField, CommandMeta
from arclet.alconna.graia import Alconna, Match, alcommand, assign
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Forward, ForwardNode, Source, Image
from graia.ariadne.model import Friend
from graia.ariadne.app import Ariadne
from graia.scheduler.timers import every_minute
from graiax.playwright import PlaywrightBrowser
from graiax.playwright.interface import Page

from app import RaianMain, Sender, Target, record, schedule
from modules.weibo import WeiboAPI, WeiboDynamic
bot = RaianMain.current()

weibo_fetch = Alconna(
    "微博",
    Args["user;O#微博用户名称", str, ArgField(completion=lambda: "比如说, 育碧")],
    Option(
        "动态",
        Args["index#从最前动态排起的第几个动态", int, -1]["page#第几页动态", int, 1],
        help_text="从微博获取指定用户的动态"
    ),
    Option("关注|增加关注", dest="follow", help_text="增加一位微博动态关注对象"),
    Option("取消关注|解除关注", dest="unfollow", help_text="解除一位微博动态关注对象"),
    Option("列出", dest="list", help_text="列出该群的微博动态关注对象"),
    meta=CommandMeta("获取指定用户的微博资料", example="$微博 育碧\n$微博 育碧 动态 1\n$微博 育碧 关注\n$微博 育碧 取消关注")
)

api = WeiboAPI(f"{bot.config.cache_dir}/plugins/weibo_data.json")


async def _handle_dynamic(
        page: Page,
        data: WeiboDynamic,
        time: datetime,
        target: int,
        name: str
):
    await page.click("html")
    await page.goto(data.url, timeout=60000, wait_until='networkidle')
    elem = page.locator("//div[@class='card-wrap']", has=page.locator("//header[@class='weibo-top m-box']"))
    elem1 = page.locator("//article[@class='weibo-main']")
    bounding = await elem.bounding_box()
    bounding1 = await elem1.bounding_box()
    bounding['height'] += bounding1['height']
    first = MessageChain(Image(data_bytes=await page.screenshot(full_page=True, clip=bounding)))
    text = MessageChain(data.text, *(Image(url=i) for i in data.img_urls))
    url = MessageChain(data.url)
    nodes = [first, text, url]
    if data.video_url:
        nodes.append(MessageChain(f"视频链接: {data.video_url}"))
    if data.retweet:
        nodes.append(MessageChain(Forward(*(await _handle_dynamic(page, data.retweet, time, target, name)))))
    return [ForwardNode(target=target, name=name, time=time, message=i) for i in nodes]


@record("微博功能")
@assign("$main")
@alcommand(weibo_fetch)
async def fetch(app: Ariadne, sender: Sender, user: Match[str]):
    if not user.available or not user.result:
        return await app.send_message(sender, MessageChain("不对劲。。。"))
    if prof := await api.get_profile(user.result, save=False, cache=False):
        return await app.send_message(
            sender, MessageChain(
                Image(url=prof.avatar),
                f"用户名: {prof.name}\n",
                f"介绍: {prof.description}\n",
                f"动态数: {prof.statuses}\n",
                f"是否可见: {'是' if prof.visitable else '否'}"
            )
        )
    return await app.send_message(sender, MessageChain("获取失败啦"))


@record("微博功能")
@assign("动态")
@alcommand(weibo_fetch)
async def fetch(
        app: Ariadne, target: Target, sender: Sender, source: Source,
        user: Match[str], index: Match[int], page: Match[int]
):
    if dynamic := await api.get_dynamic(user.result, index=index.result, page=page.result):
        browser: PlaywrightBrowser = app.launch_manager.get_interface(PlaywrightBrowser)
        async with browser.page(viewport={"width": 800, "height": 2400}) as page:
            return await app.send_message(
                sender,
                MessageChain(Forward(*(await _handle_dynamic(
                        page, dynamic, source.time, target.id, getattr(target, 'name', getattr(target, 'nickname', ""))
                    ))
                ))
            )
    return await app.send_message(sender, MessageChain("获取失败啦"))


@record("微博功能")
@assign("follow")
@alcommand(weibo_fetch)
async def fetch(app: Ariadne, sender: Sender, source: Source, user: Match[str]):
    if isinstance(sender, Friend):
        return
    if not bot.data.exist(sender.id):
        return
    prof = bot.data.get_group(sender.id)
    follower = await api.get_profile(user.result, save=True)
    if not (followers := prof.additional.get("weibo_followers")):
        followers = []
    if int(follower.id) in followers:
        return await app.send_message(sender, MessageChain(f"该群已关注 {follower.name}！请不要重复关注"))
    followers.append(int(follower.id))
    prof.additional['weibo_followers'] = followers
    bot.data.update_group(prof)
    return await app.send_message(sender, MessageChain(f"关注 {follower.name} 成功！"), quote=source.id)


@record("微博功能")
@assign("unfollow")
@alcommand(weibo_fetch)
async def fetch(app: Ariadne, sender: Sender, source: Source, user: Match[str]):
    if isinstance(sender, Friend):
        return
    if not bot.data.exist(sender.id):
        return
    prof = bot.data.get_group(sender.id)
    follower = await api.get_profile(user.result, save=False)
    if not (followers := prof.additional.get("weibo_followers")):
        followers = []
    if int(follower.id) not in followers:
        return await app.send_message(sender, MessageChain(f"该群未关注 {follower.name}！"))
    followers.remove(int(follower.id))
    prof.additional['weibo_followers'] = followers
    bot.data.update_group(prof)
    return await app.send_message(sender, MessageChain(f"解除关注 {follower.name} 成功！"), quote=source.id)


@record("微博功能")
@assign("list")
@alcommand(weibo_fetch)
async def fetch(app: Ariadne, target: Target, sender: Sender, source: Source):
    if isinstance(sender, Friend):
        return
    if not bot.data.exist(sender.id):
        return
    prof = bot.data.get_group(sender.id)
    if not (followers := prof.additional.get("weibo_followers")):
        followers = []
    if not followers:
        return await app.send_message(sender, "当前群组不存在微博关注对象")
    nodes = []
    notice = None
    for uid in followers:
        if prof := await api.get_profile(uid, save=False):
            nodes.append(
                ForwardNode(
                    target=target,
                    time=source.time,
                    message=MessageChain(
                        Image(url=prof.avatar),
                        f"用户名: {prof.name}\n",
                        f"介绍: {prof.description}\n",
                        f"动态数: {prof.statuses}\n",
                        f"是否可见: {'是' if prof.visitable else '否'}"
                    )
                )
            )
        else:
            notice = MessageChain("获取信息发生错误，建议稍后再试")
    await app.send_group_message(sender, MessageChain(Forward(*nodes)))
    if notice:
        await app.send_group_message(sender, notice)


@record("微博动态自动获取", False)
@schedule(every_minute())
async def update():
    dynamics = {}
    browser: PlaywrightBrowser = bot.app.launch_manager.get_interface(PlaywrightBrowser)
    async with browser.page(viewport={"width": 800, "height": 2400}) as page:
        for gid in bot.data.groups:
            prof = bot.data.get_group(int(gid))
            if "微博动态自动获取" in prof.disabled:
                continue
            if not (followers := prof.additional.get("weibo_followers")):
                continue
            for uid in followers:
                now = datetime.now()
                if uid in dynamics:
                    data, name = dynamics[uid]
                elif res := await api.update(int(uid)):
                    dynamics[uid] = (
                        data := await _handle_dynamic(page, res, now, bot.config.account, bot.config.bot_name),
                        name := res.user.name
                    )
                else:
                    continue
                await bot.app.send_group_message(prof.id, MessageChain(f"{name} 有一条新动态！请查收!"))
                await bot.app.send_group_message(prof.id, MessageChain(
                    Forward(*data)
                ))
    dynamics.clear()
