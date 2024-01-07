import asyncio
import random
from secrets import token_hex

from arclet.alconna import Alconna, Arg, CommandMeta, Field, Option
from arclet.alconna.graia import Match, alcommand, assign
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
from avilla.standard.core.application import ApplicationClosing
from avilla.standard.qq.elements import Forward, Node
from fastapi.responses import JSONResponse, RedirectResponse
from graia.saya.builtins.broadcast.shortcut import listen
from graia.scheduler.saya.shortcut import every
from graiax.fastapi import route
from graiax.playwright import PlaywrightBrowser, PlaywrightService
from launart import Launart
from loguru import logger
from sqlalchemy import Select

from app.config import BotConfig
from app.core import RaianBotService
from app.database import DatabaseService, Group
from app.interrupt import FunctionWaiter
from app.shortcut import accessable, allow, exclusive, picture, record
from library.weibo import WeiboAPI, WeiboDynamic, WeiboUser

from .model import WeiboFollower

bot = RaianBotService.current()

weibo_fetch = Alconna(
    "微博",
    Arg(
        "user;?#微博用户名称",
        str,
        Field(completion=lambda: "比如说, 育碧", unmatch_tips=lambda x: f"请输入微博用户名称，而不是{x}\n例如: /微博 育碧"),  # noqa: E501
    ),
    Arg("select#选择第几个用户", int, Field(default=-1, unmatch_tips=lambda x: f"请输入数字，而不是{x}")),
    Option(
        "动态",
        Arg("index#从最前动态排起的第几个动态", int, Field(default=-1, unmatch_tips=lambda x: f"请输入数字，而不是{x}"))
        + Arg("page#第几页动态", int, Field(default=1, unmatch_tips=lambda x: f"请输入数字，而不是{x}")),
        help_text="从微博获取指定用户的动态",
    ),
    Option("关注|增加关注", dest="follow", help_text="增加一位微博动态关注对象"),
    Option("取消关注|解除关注", dest="unfollow", help_text="解除一位微博动态关注对象"),
    Option("列出", dest="list", help_text="列出该群的微博动态关注对象"),
    meta=CommandMeta(
        "获取指定用户的微博资料",
        example="$微博 育碧\n$微博 育碧 动态 1\n@bot $微博 育碧 关注\n@bot $微博 育碧 取消关注",
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
):
    page = await pw.get_interface(PlaywrightBrowser).new_page(viewport={"width": 800, "height": 2400})
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
        first = Picture(RawResource(await page.screenshot(full_page=True, clip=bounding)))
    except Exception as e:
        logger.error(f"微博动态截图失败: {e}")
        first = data.text or "表情"
    finally:
        await page.close()

    imgs = data.img_urls.copy()
    return first, imgs
    # nodes: List[MessageChain] = [first, MessageChain(*imgs)] if imgs else [first]
    # if data.video_url:
    #     nodes.append(MessageChain(f"视频链接: {data.video_url}"))
    # if data.retweet:
    #     # nodes.extend(await _handle_dynamic(app, data.retweet, time, target, name, method))
    #     nodes.append(MessageChain(Forward(*(await _handle_dynamic(app, data.retweet, time, target, name, method)))))
    # # return nodes
    # return [ForwardNode(target=target, name=name, time=time, message=i) for i in nodes]


@route.route(["GET"], "/weibo/check", response_model=WeiboUser)
async def get_check(user: str, index: int = 0):
    return JSONResponse(
        (await api.get_profile_by_name(user, index, save=False, cache=False)).dict(), headers={"charset": "utf-8"}
    )


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
            return await ctx.scene.send_message(
                [
                    Picture(UrlResource(prof.avatar)),
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


@route.route(["GET"], "/weibo/get", response_model=WeiboDynamic)
async def get_fetch(user: str, index: int = -1, page: int = 1, jump: bool = False):
    prof = await api.get_profile_by_name(user, save=False, cache=False)
    if jump:
        return RedirectResponse((await api.get_dynamic(prof, index=index, page=page)).url)
    return JSONResponse((await api.get_dynamic(prof, index=index, page=page)).dict(), headers={"charset": "utf-8"})


@alcommand(weibo_fetch, comp_session={}, post=True)
@record("微博功能")
@assign("动态")
@accessable
@exclusive
async def wfetch(
    ctx: Context, user: Match[str], select: Match[int], index: Match[int], page: Match[int], pw: PlaywrightService
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
    if isinstance(ctx.account, ElizabethAccount) and nodes[1]:
        await ctx.scene.send_message([*(Picture(UrlResource(url)) for url in nodes[1])])


@alcommand(weibo_fetch, comp_session={}, need_tome=True, post=True)
@allow(ElizabethAccount)
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


@alcommand(weibo_fetch, comp_session={}, need_tome=True, post=True)
@record("微博功能")
@allow(ElizabethAccount)
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


@alcommand(weibo_fetch, comp_session={}, need_tome=True, post=True)
@allow(ElizabethAccount)
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
            nodes.append(
                Node(
                    name=conf.name,
                    uid=ctx.account.route["account"],
                    content=MessageChain(
                        [
                            Picture(UrlResource(wp.avatar)),
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


@every(5, "minute")
@record("微博动态自动获取", False)
async def update(avilla: Avilla):
    dynamics = {}
    pw = Launart.current().get_component(PlaywrightService)
    followers = set()
    if not avilla.get_accounts(account_type=ElizabethAccount):
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
                    dynamics[int(uid)] = (await _handle_dynamic(res, pw), res.user.name if res.user else "")
                    await asyncio.sleep(5)
                else:
                    continue
            except Exception as e:
                logger.error(f"WEIBO UPDATE: {e} {type(e)}")
                api.data.followers[uid] = wp
                api.data.save()
                continue
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
            try:
                account = avilla.get_account(Selector.from_follows_pattern(random.choice(group.accounts)))
            except KeyError:
                continue
            ctx = account.account.get_context(Selector().land("qq").group(group.id))
            for uid in mapping[group.id]:
                dy, name = dynamics[uid]
                await ctx.scene.send_message(f"{name} 有一条新动态！请查收!")
                await ctx.scene.send_message(dy[0])
                await ctx.scene.send_message([*(Picture(UrlResource(url)) for url in dy[1])])
                await asyncio.sleep(10)

    dynamics.clear()
    mapping.clear()
    followers.clear()
