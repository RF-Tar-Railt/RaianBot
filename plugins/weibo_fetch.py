import asyncio
import contextlib
from datetime import datetime
from typing import NamedTuple, List
from fastapi.responses import RedirectResponse, JSONResponse
from arclet.alconna import Alconna, Args, Option, Field, CommandMeta
from arclet.alconna.graia import Match, alcommand, assign, mention
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Forward, ForwardNode, Source, Image, At
from graia.ariadne.model import Friend
from graia.ariadne.connection.util import UploadMethod
from graia.ariadne.event.lifecycle import ApplicationShutdown
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.util.validator import Quoting
from graia.ariadne.util.interrupt import FunctionWaiter
from graia.ariadne.app import Ariadne
from graiax.playwright import PlaywrightBrowser
from graiax.fastapi import route
from graiax.shortcut.interrupt import FunctionWaiter
from graiax.shortcut.saya import every, listen

from app import RaianBotService, Sender, Target, record, meta_export, exclusive, accessable, RaianBotInterface
from library.weibo import WeiboAPI, WeiboDynamic, WeiboUser, WeiboError

bot = RaianBotService.current()

weibo_fetch = Alconna(
    "微博",
    Args["user;?#微博用户名称", str, Field(completion=lambda: "比如说, 育碧")]["select#选择第几个用户", int, -1],
    Option("动态", Args["index#从最前动态排起的第几个动态", int, -1]["page#第几页动态", int, 1], help_text="从微博获取指定用户的动态"),
    Option("关注|增加关注", Args["spec;?", At], dest="follow", help_text="增加一位微博动态关注对象"),
    Option("取消关注|解除关注", Args["spec;?", At], dest="unfollow", help_text="解除一位微博动态关注对象"),
    Option("列出", Args["spec;?", At], dest="list", help_text="列出该群的微博动态关注对象"),
    meta=CommandMeta("获取指定用户的微博资料", example="$微博 育碧\n$微博 育碧 动态 1\n$微博 育碧 关注\n$微博 育碧 取消关注"),
)

api = WeiboAPI(f"{bot.config.plugin_cache_dir / 'weibo_data.json'}")

@listen(ApplicationShutdown)
async def _save():
    await api.close()

class weibo_followers(NamedTuple):
    data: List[int]


meta_export(group_meta=[weibo_followers])


async def _handle_dynamic(
    app: Ariadne,
    data: WeiboDynamic,
    time: datetime,
    target: int,
    name: str,
    method: UploadMethod = UploadMethod.Group,
):
    first = MessageChain(data.text or "表情")
    browser: PlaywrightBrowser = app.launch_manager.get_interface(PlaywrightBrowser)
    with contextlib.suppress(Exception):
        async with browser.page(viewport={"width": 800, "height": 2400}) as page:
            await page.click("html")
            await page.goto(data.url, timeout=60000, wait_until="networkidle")
            elem = page.locator("//div[@class='card-wrap']", has=page.locator("//header[@class='weibo-top m-box']")).first
            elem1 = page.locator("//article[@class='weibo-main']").first
            bounding = await elem.bounding_box()
            bounding1 = await elem1.bounding_box()
            assert bounding
            assert bounding1
            bounding["height"] += bounding1["height"]
            first = MessageChain(await app.upload_image(await page.screenshot(full_page=True, clip=bounding), method))
    imgs = []
    for url in data.img_urls:
        with contextlib.suppress(Exception):
            async with app.service.client_session.get(url) as response:
                response.raise_for_status()
                imgs.append(await app.upload_image((await response.read()), method))
    nodes: List[MessageChain] = [first, MessageChain(*imgs)] if imgs else [first]
    if data.video_url:
        nodes.append(MessageChain(f"视频链接: {data.video_url}"))
    if data.retweet:
        nodes.extend(await _handle_dynamic(app, data.retweet, time, target, name, method))
        # nodes.append(MessageChain(Forward(*(await _handle_dynamic(page, data.retweet, time, target, name)))))
    return nodes
    # return [ForwardNode(target=target, name=name, time=time, message=i) for i in nodes]


@route.route(["GET"], "/weibo/check", response_model=WeiboUser)
async def get_check(user: str, index: int = 0):
    return JSONResponse(
        (await api.get_profile_by_name(user, index, save=False, cache=False)).dict(),
        headers={"charset": "utf-8"}
    )


@alcommand(weibo_fetch, comp_session={})
@record("微博功能")
@assign("$main")
@accessable
@exclusive
async def wget(app: Ariadne, sender: Sender, target: Target, user: Match[str], select: Match[int]):
    if not user.available or not user.result:
        return await app.send_message(sender, MessageChain("不对劲。。。"))
    _index = select.result
    count = -1
    with contextlib.suppress(asyncio.TimeoutError):
        profiles = await api.get_profiles(user.result)
        count = len(profiles)
    if count <= 0:
        return await app.send_message(sender, MessageChain("获取失败啦"))
    if count == 1 or 0 <= _index < count:
        prof = profiles[_index]
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
    await app.send_message(sender, MessageChain("查找到多名用户，请选择其中一位，限时 15秒"))
    await app.send_message(
        sender,
        "\n".join(
            f"{str(index).rjust(len(str(count)), '0')}. {slot.name} - {slot.description}"
            for index, slot in enumerate(profiles)
        ),
    )

    async def waiter(waiter_sender: Sender, waiter_target: Target, message: MessageChain):
        if sender.id == waiter_sender.id and waiter_target.id == target.id:
            return int(str(message)) if str(message).isdigit() else False

    res = await FunctionWaiter(
        waiter, [FriendMessage, GroupMessage], block_propagation=isinstance(sender, Friend)
    ).wait(15)
    if res:
        _index = max(res, 0)
    if _index >= count:
        return await app.send_message(sender, "别捣乱！")
    prof = profiles[max(_index, 0)]
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


@route.route(["GET"], "/weibo/get", response_model=WeiboDynamic)
async def get_fetch(user: str, index: int = -1, page: int = 1, jump: bool = False):
    prof = await api.get_profile_by_name(user, save=False, cache=False)
    if jump:
        return RedirectResponse((await api.get_dynamic(prof, index=index, page=page)).url)
    return JSONResponse((await api.get_dynamic(prof, index=index, page=page)).dict(), headers={"charset": "utf-8"})


@alcommand(weibo_fetch, comp_session={})
@record("微博功能")
@assign("动态")
@accessable
@exclusive
async def wfetch(
    app: Ariadne,
    target: Target,
    sender: Sender,
    source: Source,
    user: Match[str],
    select: Match[int],
    index: Match[int],
    page: Match[int]
):
    prof = await api.get_profile_by_name(user.result, index=select.result, save=False, cache=True)
    if not (dynamic := await api.get_dynamic(prof, index=index.result, page=page.result)):
        return await app.send_message(sender, MessageChain("获取失败啦"))
    nodes = await _handle_dynamic(
        app,
        dynamic,
        source.time,
        target.id,
        getattr(target, "name", getattr(target, "nickname", "")),
        UploadMethod.Friend if isinstance(target, Friend) else UploadMethod.Group,
    )
    for node in nodes:
        res = await app.send_message(sender, node)
    # res = await app.send_message(sender, MessageChain(Forward(*nodes)))

    async def waiter(w_sender: Sender, message: MessageChain):
        if w_sender == sender and (message.startswith("链接") or message.startswith("link")):
            return True

    resp = await FunctionWaiter(waiter, [GroupMessage, FriendMessage], decorators=[Quoting(res)]).wait(
        30, False
    )
    if not resp:
        return
    return await app.send_message(sender, MessageChain(dynamic.url))


@alcommand(weibo_fetch, comp_session={})
@record("微博功能")
@mention("spec")
@assign("follow")
@accessable
@exclusive
async def wfollow(
    app: Ariadne,
    sender: Sender,
    source: Source,
    user: Match[str],
    select: Match[int],
    interface: RaianBotInterface
):
    if isinstance(sender, Friend):
        return
    if not interface.data.exist(sender.id):
        return
    data = interface.data.get_group(sender.id)
    follower = await api.get_profile_by_name(user.result, index=select.result, save=True)
    followers = data.get(weibo_followers, weibo_followers([]))
    if int(follower.id) in followers.data:
        return await app.send_message(sender, MessageChain(f"该群已关注 {follower.name}！请不要重复关注"))
    followers.data.append(int(follower.id))
    data.set(followers)
    interface.data.update_group(data)
    return await app.send_message(sender, MessageChain(f"关注 {follower.name} 成功！"), quote=source.id)


@alcommand(weibo_fetch, comp_session={})
@record("微博功能")
@mention("spec")
@assign("unfollow")
@accessable
@exclusive
async def wunfollow(
    app: Ariadne,
    sender: Sender,
    source: Source,
    user: Match[str],
    select: Match[int],
    interface: RaianBotInterface
):
    if isinstance(sender, Friend):
        return
    if not interface.data.exist(sender.id):
        return
    prof = interface.data.get_group(sender.id)
    follower = await api.get_profile_by_name(user.result, index=select.result, save=True)
    followers = prof.get(weibo_followers, weibo_followers([]))
    if int(follower.id) not in followers.data:
        return await app.send_message(sender, MessageChain(f"该群未关注 {follower.name}！"))
    followers.data.remove(int(follower.id))
    prof.set(followers)
    interface.data.update_group(prof)
    return await app.send_message(sender, MessageChain(f"解除关注 {follower.name} 成功！"), quote=source.id)


@alcommand(weibo_fetch, comp_session={})
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
        if wp := await api.get_profile(uid, save=False):
            nodes.append(
                ForwardNode(
                    target=target,
                    time=source.time,
                    message=MessageChain(
                        Image(url=wp.avatar),
                        f"用户名: {wp.name}\n",
                        f"介绍: {wp.description}\n",
                        f"动态数: {wp.statuses}\n",
                        f"是否可见: {'是' if wp.visitable else '否'}",
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
    visited = {}
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
                if uid in visited.get(gid, []):
                    continue
                wp = await api.get_profile(int(uid))
                if not wp:
                    continue
                wp = wp.copy()
                try:
                    now = datetime.now()
                    if uid in dynamics:
                        dy, name = dynamics[uid]
                    elif res := await api.update(int(uid)):
                        dynamics[uid] = (
                            dy := await _handle_dynamic(app, res, now, config.account, config.bot_name),
                            name := res.user.name,
                        )
                    else:
                        continue
                    await app.send_group_message(prof.id, MessageChain(f"{name} 有一条新动态！请查收!"))
                    for node in dy:
                        await app.send_group_message(prof.id, node)
                    await asyncio.sleep(1)
                    visited.setdefault(gid, []).append(uid)
                    # await app.send_group_message(prof.id, MessageChain(Forward(*data)))
                except (ValueError, TypeError, IndexError, KeyError, asyncio.TimeoutError):
                    api.data.followers[uid] = wp
                    await api.data.save()
                    continue
    dynamics.clear()
    visited.clear()
