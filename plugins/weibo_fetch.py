from datetime import datetime
from typing import NamedTuple, List
from fastapi.responses import RedirectResponse, JSONResponse
from arclet.alconna import Args, Option, Field, CommandMeta
from arclet.alconna.graia import Alconna, Match, alcommand, assign, mention
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Forward, ForwardNode, Source, Image, At
from graia.ariadne.model import Friend
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.util.validator import Quoting
from graia.ariadne.app import Ariadne
from graiax.playwright import PlaywrightBrowser
from graiax.fastapi import route
from graiax.shortcut.interrupt import FunctionWaiter
from graiax.shortcut.saya import every
from playwright.async_api import TimeoutError, Page

from app import RaianBotService, Sender, Target, record, meta_export, exclusive, accessable, RaianBotInterface
from library.weibo import WeiboAPI, WeiboDynamic, WeiboUser

bot = RaianBotService.current()

weibo_fetch = Alconna(
    "微博",
    Args["user;?#微博用户名称", str, Field(completion=lambda: "比如说, 育碧")],
    Option("动态", Args["index#从最前动态排起的第几个动态", int, -1]["page#第几页动态", int, 1], help_text="从微博获取指定用户的动态"),
    Option("关注|增加关注", Args["spec;?", At], dest="follow", help_text="增加一位微博动态关注对象"),
    Option("取消关注|解除关注", Args["spec;?", At], dest="unfollow", help_text="解除一位微博动态关注对象"),
    Option("列出", Args["spec;?", At], dest="list", help_text="列出该群的微博动态关注对象"),
    meta=CommandMeta("获取指定用户的微博资料", example="$微博 育碧\n$微博 育碧 动态 1\n$微博 育碧 关注\n$微博 育碧 取消关注"),
)

api = WeiboAPI(f"{bot.config.plugin_cache_dir / 'weibo_data.json'}")


class weibo_followers(NamedTuple):
    data: List[int]


meta_export(group_meta=[weibo_followers])


async def _handle_dynamic(page: Page, data: WeiboDynamic, time: datetime, target: int, name: str):
    try:
        await page.click("html")
        await page.goto(data.url, timeout=60000, wait_until="networkidle")
        elem = page.locator("//div[@class='card-wrap']", has=page.locator("//header[@class='weibo-top m-box']")).first
        elem1 = page.locator("//article[@class='weibo-main']").first
        bounding = await elem.bounding_box()
        bounding1 = await elem1.bounding_box()
        assert bounding
        assert bounding1
        bounding["height"] += bounding1["height"]
        first = MessageChain(Image(data_bytes=await page.screenshot(full_page=True, clip=bounding)))
    except (TimeoutError, TypeError):
        first = None
    nodes = [MessageChain(*(Image(url=i) for i in data.img_urls))] if data.img_urls else []
    nodes.insert(0, first or MessageChain(data.text or "表情"))
    if data.video_url:
        nodes.append(MessageChain(f"视频链接: {data.video_url}"))
    if data.retweet:
        nodes.append(MessageChain(Forward(*(await _handle_dynamic(page, data.retweet, time, target, name)))))
    return [ForwardNode(target=target, name=name, time=time, message=i) for i in nodes]


@route.route(["GET"], "/weibo/check", response_model=WeiboUser)
async def get_check(user: str):
    return JSONResponse((await api.get_profile(user, save=False, cache=False)).dict(), headers={"charset": "utf-8"})


@alcommand(weibo_fetch)
@record("微博功能")
@assign("$main")
@accessable
@exclusive
async def wget(app: Ariadne, sender: Sender, user: Match[str]):
    if not user.available or not user.result:
        return await app.send_message(sender, MessageChain("不对劲。。。"))
    if prof := await api.get_profile(user.result, save=False, cache=False):
        return await app.send_message(
            sender,
            MessageChain(
                Image(url=prof.avatar),
                f"用户名: {prof.name}\n",
                f"介绍: {prof.description}\n",
                f"动态数: {prof.statuses}\n",
                f"是否可见: {'是' if prof.visitable else '否'}",
            ),
        )
    return await app.send_message(sender, MessageChain("获取失败啦"))


@route.route(["GET"], "/weibo/get", response_model=WeiboDynamic)
async def get_fetch(user: str, index: int = -1, page: int = 1, jump: bool = False):
    if jump:
        return RedirectResponse((await api.get_dynamic(user, index=index, page=page)).url)
    return JSONResponse((await api.get_dynamic(user, index=index, page=page)).dict(), headers={"charset": "utf-8"})


@alcommand(weibo_fetch)
@record("微博功能")
@assign("动态")
@accessable
@exclusive
async def wfetch(
    app: Ariadne, target: Target, sender: Sender, source: Source, user: Match[str], index: Match[int], page: Match[int]
):
    if dynamic := await api.get_dynamic(user.result, index=index.result, page=page.result):
        browser: PlaywrightBrowser = app.launch_manager.get_interface(PlaywrightBrowser)
        async with browser.page(viewport={"width": 800, "height": 2400}) as _page:
            nodes = await _handle_dynamic(
                _page,
                dynamic,
                source.time,
                target.id,
                getattr(target, "name", getattr(target, "nickname", "")),
            )
            for node in nodes:
                res = await app.send_message(sender, node.message_chain)
            # res = await app.send_message(sender, MessageChain(Forward(*nodes)))

            async def waiter(w_sender: Sender, message: MessageChain):
                if w_sender == sender and message.startswith("链接"):
                    return True

            resp = await FunctionWaiter(waiter, [GroupMessage, FriendMessage], decorators=[Quoting(res)]).wait(
                30, False
            )
            if not resp:
                return
            return await app.send_message(sender, MessageChain(dynamic.url))
    return await app.send_message(sender, MessageChain("获取失败啦"))


@alcommand(weibo_fetch)
@record("微博功能")
@mention("spec")
@assign("follow")
@accessable
@exclusive
async def wfollow(app: Ariadne, sender: Sender, source: Source, user: Match[str], interface: RaianBotInterface):
    if isinstance(sender, Friend):
        return
    if not interface.data.exist(sender.id):
        return
    prof = interface.data.get_group(sender.id)
    follower = await api.get_profile(user.result, save=True)
    followers = prof.get(weibo_followers, weibo_followers([]))
    if int(follower.id) in followers.data:
        return await app.send_message(sender, MessageChain(f"该群已关注 {follower.name}！请不要重复关注"))
    followers.data.append(int(follower.id))
    prof.set(followers)
    interface.data.update_group(prof)
    return await app.send_message(sender, MessageChain(f"关注 {follower.name} 成功！"), quote=source.id)


@alcommand(weibo_fetch)
@record("微博功能")
@mention("spec")
@assign("unfollow")
@accessable
@exclusive
async def wunfollow(app: Ariadne, sender: Sender, source: Source, user: Match[str], interface: RaianBotInterface):
    if isinstance(sender, Friend):
        return
    if not interface.data.exist(sender.id):
        return
    prof = interface.data.get_group(sender.id)
    follower = await api.get_profile(user.result, save=False)
    followers = prof.get(weibo_followers, weibo_followers([]))
    if int(follower.id) not in followers.data:
        return await app.send_message(sender, MessageChain(f"该群未关注 {follower.name}！"))
    followers.data.remove(int(follower.id))
    prof.set(followers)
    interface.data.update_group(prof)
    return await app.send_message(sender, MessageChain(f"解除关注 {follower.name} 成功！"), quote=source.id)


@alcommand(weibo_fetch)
@record("微博功能")
@mention("spec")
@assign("list")
@accessable
@exclusive
async def wlist(app: Ariadne, target: Target, sender: Sender, source: Source, interface: RaianBotInterface):
    if isinstance(sender, Friend):
        return
    if not interface.data.exist(sender.id):
        return
    prof = interface.data.get_group(sender.id)
    if not (followers := prof.get(weibo_followers)) or not followers.data:
        return await app.send_message(sender, "当前群组不存在微博关注对象")
    nodes = []
    notice = None
    for uid in followers.data:
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
                        f"是否可见: {'是' if prof.visitable else '否'}",
                    ),
                )
            )
        else:
            notice = MessageChain("获取信息发生错误，建议稍后再试")
    await app.send_group_message(sender, MessageChain(Forward(*nodes)))
    if notice:
        await app.send_group_message(sender, notice)


@every(1, "minute")
@record("微博动态自动获取", False)
async def update():
    dynamics = {}
    browser: PlaywrightBrowser = Ariadne.current().launch_manager.get_interface(PlaywrightBrowser)
    async with browser.page(viewport={"width": 800, "height": 2400}) as page:
        for account, app in Ariadne.instances.items():
            interface = app.launch_manager.get_interface(RaianBotInterface).bind(account)
            data = interface.data
            config = interface.config
            for gid in data.groups:
                if not data.exist(int(gid)):
                    continue
                prof = data.get_group(int(gid))
                if "微博动态自动获取" in prof.disabled:
                    continue
                if not (followers := prof.get(weibo_followers)):
                    continue
                for uid in followers.data:
                    wp = (await api.get_profile(int(uid))).copy()
                    try:
                        now = datetime.now()
                        if uid in dynamics:
                            dy, name = dynamics[uid]
                        elif res := await api.update(int(uid)):
                            dynamics[uid] = (
                                dy := await _handle_dynamic(page, res, now, config.account, config.bot_name),
                                name := res.user.name,
                            )
                        else:
                            continue
                        await app.send_group_message(prof.id, MessageChain(f"{name} 有一条新动态！请查收!"))
                        for node in dy:
                            await app.send_group_message(prof.id, node.message_chain)
                        # await app.send_group_message(prof.id, MessageChain(Forward(*data)))
                    except (ValueError, TypeError, IndexError, KeyError):
                        api.data.followers[uid] = wp
                        await api.data.save()
                        continue
    dynamics.clear()
