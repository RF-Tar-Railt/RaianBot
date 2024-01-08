from arclet.alconna import Alconna, Args, CommandMeta, Option
from arclet.alconna.graia import Match, alcommand, assign
from avilla.core import Context, MessageChain, MessageReceived, MessageSent, Picture, RawResource
from avilla.core.elements import Face, Notice
from avilla.core.exceptions import ActionFailed
from avilla.elizabeth.account import ElizabethAccount
from avilla.standard.core.profile import Nick
from avilla.standard.qq.elements import MarketFace
from graia.saya.builtins.broadcast.shortcut import listen, priority
from graiax.playwright import PlaywrightBrowser, PlaywrightService
from sqlalchemy import select

from app.config import BotConfig
from app.core import RaianBotService
from app.database import DatabaseService, Group
from app.interrupt import FunctionWaiter
from app.message import display
from app.shortcut import accessable, allow, exclusive, record
from library.ak_closure_talk import ArknightsClosureStore
from library.ak_closure_talk.exceptions import CharacterNotExist, RecordMaxExceed, SessionAlreadyExist, SessionNotExist

bot = RaianBotService.current()
store = ArknightsClosureStore()

closure = Alconna(
    "罗德岛聊天",
    Option("开始|开始记录|记录", dest="start", help_text="开始记录聊天内容，输入‘$结束‘或’$取消’结束记录"),
    Option("创建", Args["count", int, 1000], dest="create", help_text="创建一个新聊天室"),
    Option("绑定", Args["name", str], dest="bind", help_text="绑定一个角色"),
    Option("重置", dest="reset"),
    meta=CommandMeta("创建罗德岛聊天室并制图", usage="注意: 该命令不需要 “渊白” 开头", extra={"supports": {"mirai"}}),
)

cache_dir = bot.config.plugin_data_dir / "closure"
cache_dir.mkdir(parents=True, exist_ok=True)


@alcommand(closure, post=True, send_error=True)
@record("closure")
@assign("$main")
@allow(ElizabethAccount)
@exclusive
@accessable
async def _help(ctx: Context):
    return await ctx.scene.send_message(
        "[ClosureTalk] 该命令用以创建罗德岛聊天室并制图\n"
        "命令用法：\n"
        "罗德岛聊天 创建 (聊天上限)：创建新的聊天室；默认聊天上限为 1000\n"
        "罗德岛聊天 绑定 角色名：绑定一个角色；不绑定则使用 群昵称\n"
        "角色名或群昵称可通过加上‘#序号’选择该角色其他头像，例如：德克萨斯#2 可选择精二头像\n"
        "罗德岛聊天 开始：开始记录聊天内容；输入‘$结束‘或’$取消’结束记录\n"
        "罗德岛聊天 重置：重置聊天室"
    )


@alcommand(closure, post=True, send_error=True)
@record("closure")
@assign("reset")
@allow(ElizabethAccount)
@exclusive
@accessable
async def _reset(ctx: Context):
    group_id = ctx.scene.channel
    store.end(group_id)
    if group_id in (rooms := bot.cache.setdefault("$closure_rooms", [])):
        rooms.remove(group_id)
    return await ctx.scene.send_message("[ClosureTalk] 重置完毕")


@alcommand(closure, post=True, send_error=True)
@record("closure")
@assign("bind")
@allow(ElizabethAccount)
@exclusive
@accessable
async def _bind(ctx: Context, name: Match[str]):
    group_id = ctx.scene.channel
    target_id = ctx.client.user
    try:
        if char := store.add_char(group_id, target_id, name.result):
            return await ctx.scene.send_message(f"[ClosureTalk] 绑定成功: {char.id}")
        return await ctx.scene.send_message("[ClosureTalk] 未找到角色，使用成员头像")
    except SessionNotExist as e:
        return await ctx.scene.send_message(str(e))


@alcommand(closure, post=True, send_error=True)
@record("closure")
@assign("create")
@allow(ElizabethAccount)
@exclusive
@accessable
async def _create(ctx: Context, count: Match[int]):
    try:
        store.start(ctx.scene.channel, count.result)
        return await ctx.scene.send_message("[ClosureTalk] 创建房间成功")
    except SessionAlreadyExist as e:
        return await ctx.scene.send_message(str(e))


@alcommand(closure, post=True, send_error=True)
@record("closure")
@assign("start")
@allow(ElizabethAccount)
@exclusive
@accessable
async def _start(ctx: Context, pw: PlaywrightService):
    browser: PlaywrightBrowser = pw.get_interface(PlaywrightBrowser)
    group_id = ctx.scene.channel
    if group_id not in store.session:
        return await ctx.scene.send_message("[ClosureTalk] 会话未存在")

    if group_id in (rooms := bot.cache.setdefault("$closure_rooms", [])):
        return
    rooms.append(group_id)
    await ctx.scene.send_message("[ClosureTalk] 记录开始！输入‘$结束‘或’$取消’结束记录")

    async def waiter(w_ctx: Context, message: MessageChain):
        if w_ctx.scene.pattern != ctx.scene.pattern:
            return
        if message.startswith("罗德岛聊天"):
            return
        if message.startswith("$结束") or message.startswith("$取消"):
            return False
        message = message.exclude(Face, MarketFace).merge()
        for index, elem in enumerate(message.content):
            if isinstance(elem, Notice) and not elem.display:
                try:
                    nick = await ctx.pull(Nick, elem.target)
                    elem.display = nick.nickname or nick.name
                except (ActionFailed, NotImplementedError):
                    elem.display = elem.target.last_value
        msg = display(message)
        if not msg:
            return
        try:
            try:
                store.add_content(msg, w_ctx.scene.channel, w_ctx.client.user)
            except CharacterNotExist:
                try:
                    nick = await ctx.client.nick()
                    name = nick.nickname or nick.name
                except (ActionFailed, NotImplementedError):
                    name = w_ctx.client.user
                store.add_char(w_ctx.scene.channel, w_ctx.client.user, name)
                store.add_content(msg, w_ctx.scene.channel, w_ctx.client.user)
        except (RecordMaxExceed, SessionNotExist):
            return False
        return True

    while True:
        wat = FunctionWaiter(waiter, [MessageReceived])
        res = await wat.wait(180, False)
        if res is None:
            continue
        if res is False:
            break

    file = cache_dir / f"{group_id}.html"
    with file.open("w+", encoding="utf-8") as f:
        f.write(store.export(group_id))
    try:
        await ctx.scene.send_message("[ClosureTalk] 记录结束，正在渲染中。。。")
        async with browser.page(
            viewport={"width": 500, "height": 1},
            device_scale_factor=1.5,
        ) as page:
            await page.goto(file.absolute().as_uri())
            # await page.set_content(store.export(str(sender.id)))
            img = await page.screenshot(type="jpeg", quality=80, full_page=True, scale="device")
            await ctx.scene.send_message(Picture(RawResource(img)))
    finally:
        store.end(group_id)
        rooms.remove(group_id)


@listen(MessageSent)
@record("closure", require=False)
@priority(24)
@accessable
async def _record_self(event: MessageSent, db: DatabaseService, config: BotConfig):
    gid = event.context.scene.channel
    if gid not in bot.cache.setdefault("$closure_rooms", []):
        return
    async with db.get_session() as session:
        group = (
            await session.scalars(select(Group).where(Group.id == gid).where(Group.in_blacklist is False))
        ).one_or_none()
        if not group:
            return
        if "closure" in group.disabled:
            return
    msg = display(event.message.content)
    if msg.startswith("[ClosureTalk]"):
        return
    try:
        try:
            store.add_content(msg, str(gid), event.account.route["account"])
        except CharacterNotExist:
            store.add_char(str(gid), event.account.route["account"], config.name)
            store.add_content(msg, str(gid), event.account.route["account"])
    except RecordMaxExceed:
        return False
