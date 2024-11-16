import asyncio
import random
from datetime import datetime
from secrets import token_hex

from arclet.alconna import Alconna, Arg, CommandMeta, Field, Option
from arclet.alconna.avilla import Match, Query, alcommand, assign
from avilla.core import (
    ActionFailed,
    Avilla,
    Context,
    MessageChain,
    MessageReceived,
    Notice,
    Picture,
    RawResource,
    Selector,
    Text,
    UrlResource,
)
from avilla.elizabeth.account import ElizabethAccount
from avilla.onebot.v11.account import OneBot11Account
from avilla.standard.core.application import ApplicationClosing
from avilla.standard.qq.elements import Forward, Node
from graia.saya.builtins.broadcast.shortcut import listen
from graia.scheduler.saya.shortcut import every
from graiax.playwright import PlaywrightService
from launart import Launart
from loguru import logger
from sqlalchemy import Select

from app.config import BotConfig
from app.core import RaianBotService
from app.database import DatabaseService, Group
from app.interrupt import FunctionWaiter
from app.shortcut import accessable, allow, exclusive, picture, record
from library.weibo import WeiboAPI, WeiboDynamic

from .config import WeiboConfig
from .model import WeiboFollower

bot = RaianBotService.current()
weibo_config = bot.config.plugin.get(WeiboConfig)
weibo_fetch = Alconna(
    "微博",
    Arg(
        "user;?#微博用户名称",
        str,
        Field(
            completion=lambda: "比如说, 育碧", unmatch_tips=lambda x: f"请输入微博用户名称，而不是{x}\n例如: /微博 育碧"
        ),  # noqa: E501
    ),
    Arg("select#选择第几个用户", int, Field(default=-1, unmatch_tips=lambda x: f"请输入数字，而不是{x}")),
    Option(
        "动态",
        Arg("index?#从最前动态排起的第几个动态", int, Field(unmatch_tips=lambda x: f"请输入数字，而不是{x}"))
        + Arg("page?#第几页动态", int, Field(unmatch_tips=lambda x: f"请输入数字，而不是{x}")),
        help_text="从微博获取指定用户的动态",
    ),
    Option("关注|增加关注", dest="follow", help_text="增加一位微博动态关注对象"),
    Option("取消关注|解除关注", dest="unfollow", help_text="解除一位微博动态关注对象"),
    Option("列出", dest="list", help_text="列出该群的微博动态关注对象"),
    meta=CommandMeta(
        "获取指定用户的微博资料",
        example="$微博 育碧\n$微博 育碧 动态 1\n$微博 育碧 关注\n$微博 育碧 取消关注",
        extra={"supports": {"mirai", "qqapi"}},
    ),
)

api = WeiboAPI(f"{bot.config.plugin_data_dir / 'weibo_data.json'}")


@listen(ApplicationClosing)
async def _save():
    await api.close()


async def _handle_dynamic(
    data: WeiboDynamic,
    pw: PlaywrightService,
    url_imgs: bool = False,
):
    async with pw.page(viewport={"width": 800, "height": 2400}) as page:
        try:
            await page.click("html")
            await page.goto(data.url, timeout=20000, wait_until="networkidle")
            elem = page.locator(
                "//div[@class='card-wrap']", has=page.locator("//header[@class='weibo-top m-box']")
            ).first
            elem1 = page.locator("//article[@class='weibo-main']").first
            bounding = await elem.bounding_box()
            bounding1 = await elem1.bounding_box()
            assert bounding
            assert bounding1
            bounding["height"] += bounding1["height"]
            first = Picture(RawResource(await page.screenshot(full_page=True, clip=bounding)))
        except Exception as e:
            logger.error(f"微博动态截图失败: {e}")
            first = data.text or "表情"

    imgs: list[Picture] = []
    for url in data.img_urls:
        async with api.session.get(url) as resp:
            if url_imgs and bot.config.platform.tencentcloud:
                url = await bot.upload_to_cos(await resp.read(), f"weibo_dym_{token_hex(16)}.png")
                imgs.append(Picture(UrlResource(url)))
            else:
                imgs.append(Picture(RawResource(await resp.read())))
    return first, imgs


async def _handle_dynamic_forward(
    data: WeiboDynamic, pw: PlaywrightService, uid: str, name: str, url_imgs: bool = False
):
    first, imgs = await _handle_dynamic(data, pw, url_imgs)
    nodes: list[MessageChain] = [MessageChain([first]), MessageChain(imgs)] if imgs else [MessageChain([first])]
    if data.video_url:
        nodes.append(MessageChain(f"视频链接: {data.video_url}"))
    if data.retweet:
        nodes.extend(node.content for node in await _handle_dynamic_forward(data.retweet, pw, uid, name, url_imgs))  # type: ignore
    return [Node(uid=uid, name=name, time=datetime.now(), content=i) for i in nodes]


@alcommand(weibo_fetch, comp_session={}, post=True)
@record("微博功能")
@assign("$main")
@accessable
@exclusive
async def wget(ctx: Context, user: Match[str], select: Match[int]):
    if not user.available or not user.result:
        return await ctx.scene.send_message("请指定微博用户名\n例如: /微博 育碧")
    _index = select.result
    count = -1
    profiles = []
    try:
        profiles = await api.get_profiles(user.result)
        count = len(profiles)
    except Exception as e:
        logger.error(f"WEIBO GET: {e} {type(e)}")
        return await ctx.scene.send_message(f"获取用户信息发生错误: {e!r}")
    if count <= 0:
        return await ctx.scene.send_message("获取失败啦")
    if count == 1 or 0 <= _index < count:
        prof = profiles[_index]
    else:
        await ctx.scene.send_message("查找到多名用户，请选择其中一位，限时 15秒")
        await ctx.scene.send_message(
            "\n".join(
                f"{str(index).rjust(len(str(count)), '0')}. {slot.name} - {slot.description.replace('.', '. ')}"
                for index, slot in enumerate(profiles)
            ),
        )

        async def waiter(waiter_ctx: Context, message: MessageChain):
            if waiter_ctx.client == ctx.client:
                msg = str(message.exclude(Notice)).lstrip()
                return int(msg) if msg.isdigit() else False

        res = await FunctionWaiter(
            waiter,
            [MessageReceived],
            block_propagation=ctx.client.follows("::friend") or ctx.client.follows("::guild.user"),
        ).wait(15)
        if res:
            _index = max(res, 0)
        if _index >= count:
            return await ctx.scene.send_message("别捣乱！")
        prof = profiles[max(_index, 0)]
        try:
            async with api.session.get(prof.avatar) as resp:
                pic = Picture(RawResource(await resp.read()))
            return await ctx.scene.send_message(
                [
                    pic,
                    Text(
                        f"用户名: {prof.name}\n"
                        f"介绍: {prof.description.replace('.', '. ')}\n"
                        f"动态数: {prof.statuses}\n"
                        f"是否可见: {'是' if prof.visitable else '否'}"
                    ),
                ]
            )
        except ActionFailed:
            return await ctx.scene.send_message(
                f"""\
用户名: {prof.name}
介绍: {prof.description.replace('.', '. ')}
动态数: {prof.statuses}
是否可见: {'是' if prof.visitable else '否'}
"""
            )


@alcommand(weibo_fetch, comp_session={}, post=True)
@record("微博功能")
@assign("动态")
@accessable
@exclusive
async def wfetch(
    ctx: Context,
    user: Match[str],
    select: Match[int],
    pw: PlaywrightService,
    index: Query[int] = Query("动态.index", -1),
    page: Query[int] = Query("动态.page", 1),
):
    try:
        prof = await api.get_profile_by_name(user.result, index=select.result, save=False, cache=True)
        dynamic = await api.get_dynamic(prof, index=index.result, page=page.result)
    except Exception as e:
        logger.error(f"WEIBO FETCH: {e} {type(e)}")
        return await ctx.scene.send_message(f"获取动态发生错误: {e!r}")

    nodes = await _handle_dynamic(dynamic, pw)
    try:
        await ctx.scene.send_message(nodes[0])
    except Exception as e:
        if isinstance(nodes[0], Picture):
            url = await bot.upload_to_cos(nodes[0].resource.data, f"weibo_dym_{token_hex(16)}.png")  # type: ignore
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed:
                return await ctx.scene.send_message(picture(url, ctx))
        await ctx.scene.send_message(str(e))
    if isinstance(ctx.account, (ElizabethAccount, OneBot11Account)) and nodes[1]:
        await ctx.scene.send_message(nodes[1])


@alcommand(weibo_fetch, comp_session={}, post=True)
@allow(ElizabethAccount, OneBot11Account)
@record("微博功能")
@assign("follow")
@accessable
@exclusive
async def wfollow(ctx: Context, user: Match[str], select: Match[int], db: DatabaseService):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return await ctx.scene.send_message("该指令对私聊无效果")
    try:
        follower = await api.get_profile_by_name(user.result, index=select.result, save=True)
    except Exception as e:
        logger.error(f"WEIBO FOLLOW: {e} {type(e)}")
        return await ctx.scene.send_message(f"获取用户信息发生错误: {e!r}")

    async with db.get_session() as session:
        rec = (
            await session.scalars(
                Select(WeiboFollower)
                .where(WeiboFollower.id == ctx.scene.channel)
                .where(WeiboFollower.wid == int(follower.id))
            )
        ).one_or_none()
        if rec:
            return await ctx.scene.send_message(f"该群已关注 {follower.name}！请不要重复关注")
        session.add(WeiboFollower(id=ctx.scene.channel, wid=int(follower.id)))
        await session.commit()
        return await ctx.scene.send_message(f"关注 {follower.name} 成功！")


@alcommand(weibo_fetch, comp_session={}, post=True)
@record("微博功能")
@allow(ElizabethAccount, OneBot11Account)
@assign("unfollow")
@accessable
@exclusive
async def wunfollow(ctx: Context, user: Match[str], select: Match[int], db: DatabaseService):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return await ctx.scene.send_message("该指令对私聊无效果")
    try:
        follower = await api.get_profile_by_name(user.result, index=select.result, save=True)
    except Exception as e:
        logger.error(f"WEIBO FOLLOW: {e} {type(e)}")
        return await ctx.scene.send_message(f"获取用户信息发生错误: {e!r}")

    async with db.get_session() as session:
        rec = (
            await session.scalars(
                Select(WeiboFollower)
                .where(WeiboFollower.id == ctx.scene.channel)
                .where(WeiboFollower.wid == int(follower.id))
            )
        ).one_or_none()
        if not rec:
            return await ctx.scene.send_message(f"该群未关注 {follower.name}！")
        await session.delete(rec)
        await session.commit()
        return await ctx.scene.send_message(f"解除关注 {follower.name} 成功！")


@alcommand(weibo_fetch, comp_session={}, post=True)
@allow(ElizabethAccount, OneBot11Account)
@record("微博功能")
@assign("list")
@accessable
@exclusive
async def wlist(ctx: Context, db: DatabaseService, conf: BotConfig):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return await ctx.scene.send_message("该指令对私聊无效果")
    async with db.get_session() as session:
        followers = (await session.scalars(Select(WeiboFollower).where(WeiboFollower.id == ctx.scene.channel))).all()
        if not followers:
            return await ctx.scene.send_message("当前群组不存在微博关注对象")
    notice = None
    nodes = []
    for follower in followers:
        try:
            wp = await api.get_profile(follower.wid, save=False)
            async with api.session.get(wp.avatar) as resp:
                pic = Picture(RawResource(await resp.read()))
            nodes.append(
                Node(
                    name=conf.name,
                    uid=ctx.account.route["account"],
                    content=MessageChain(
                        [
                            pic,
                            Text(
                                f"用户名: {wp.name}\n"
                                f"介绍: {wp.description}\n"
                                f"动态数: {wp.statuses}\n"
                                f"是否可见: {'是' if wp.visitable else '否'}"
                            ),
                        ]
                    ),
                )
            )
        except Exception as e:
            logger.error(f"WEIBO LIST: {e} {type(e)}")
            notice = f"获取用户信息发生错误: {e!r}"
    if nodes:
        await ctx.scene.send_message(Forward(*nodes))
    if notice:
        await ctx.scene.send_message(notice)


FIRST_STARTUP = False


@every(3, "minute")
@record("微博动态自动获取", False)
async def update(avilla: Avilla):
    global FIRST_STARTUP
    dynamics = {}
    pw = Launart.current().get_component(PlaywrightService)
    followers = set()
    if not avilla.get_accounts(account_type=(ElizabethAccount, OneBot11Account)):
        return
    async with bot.db.get_session() as session:
        mapping = {}
        for follower in (await session.scalars(Select(WeiboFollower))).all():
            mapping.setdefault(follower.id, []).append(follower.wid)
            followers.add(follower.wid)
        for uid in followers:
            wp = await api.get_profile(int(uid))
            wp = wp.copy()
            try:
                if res := await api.update(int(uid)):
                    dynamics[int(uid)] = res
                else:
                    continue
            except Exception as e:
                logger.error(f"WEIBO UPDATE: {e} {type(e)}")
                api.data.followers[uid] = wp
                api.data.save()
                continue
        if not FIRST_STARTUP:
            FIRST_STARTUP = True
            dynamics.clear()
            mapping.clear()
            followers.clear()
            return
        for group_id in list(mapping.keys()):
            union = set(mapping[group_id]).intersection(dynamics.keys())
            if not union:
                del mapping[group_id]
            else:
                mapping[group_id] = list(union)
        for group in (
            await session.scalars(Select(Group).where(Group.platform == "qq").where(Group.id.in_(mapping)))
        ).all():
            if "微博动态自动获取" in group.disabled:
                continue
            accounts = []
            for account in group.accounts:
                _route = Selector.from_follows_pattern(account)
                if _route in avilla.accounts and isinstance(
                    (acc := avilla.get_account(_route)).account, (ElizabethAccount, OneBot11Account)
                ):
                    accounts.append(acc.account)
            if not accounts:
                continue
            choose = random.choice(accounts)
            self_info = next((info for info in bot.config.bots if info.ensure(choose)), None)  # type: ignore
            if not self_info:
                continue
            ctx = choose.get_context(Selector().land("qq").group(group.id))
            for uid in mapping[group.id]:
                if uid not in dynamics:
                    continue
                slot = dynamics[uid]
                if isinstance(slot, WeiboDynamic):
                    name = slot.user.name if slot.user else f"微博用户{uid}"
                    if weibo_config.dynamic_forward:
                        nodes = await _handle_dynamic_forward(slot, pw, self_info.account, self_info.name)
                        dy = Forward(nodes=nodes)
                    else:
                        dy, _ = await _handle_dynamic(slot, pw, True)
                    dynamics[uid] = (dy, name)
                else:
                    dy, name = slot  # type: ignore
                await ctx.scene.send_message(f"{name} 有一条新动态！请查收!")
                await ctx.scene.send_message(dy)
                await asyncio.sleep(10)

    dynamics.clear()
    mapping.clear()
    followers.clear()
