from pathlib import Path
from arclet.alconna import Args, Option, CommandMeta
from arclet.alconna.graia import Alconna, alcommand, assign, Match
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Face, MarketFace, At
from graia.ariadne.event.message import ActiveGroupMessage, GroupMessage
from graia.ariadne.model import Group, Member
from graiax.shortcut.interrupt import FunctionWaiter
from graiax.playwright import PlaywrightBrowser
from graiax.shortcut.saya import listen, priority
from library.ak_closure_talk import ArknightsClosureStore
from library.ak_closure_talk.exceptions import *
from app import BotConfig, RaianBotService

bot = RaianBotService.current()
store = ArknightsClosureStore()

closure = Alconna(
    [""],
    "罗德岛聊天",
    Option("开始|开始记录|记录", dest="start", help_text="开始记录聊天内容，输入‘$结束‘或’$取消’结束记录"),
    Option("创建", Args["count", int, 1000], dest="create", help_text="创建一个新聊天室"),
    Option("绑定", Args["name", str], dest="bind", help_text="绑定一个角色"),
    Option("重置", dest="reset"),
    meta=CommandMeta("创建罗德岛聊天室并制图", usage="注意: 该命令不需要 “渊白” 开头"),
)

rooms = []
cache_dir = Path(bot.config.cache_dir) / "plugins" / "closure"
cache_dir.mkdir(parents=True, exist_ok=True)


@alcommand(closure, private=False)
@assign("$main")
async def _help(app: Ariadne, sender: Group):
    return await app.send_message(
        sender,
        (
            "[ClosureTalk] 该命令用以创建罗德岛聊天室并制图\n"
            "命令用法：\n"
            "罗德岛聊天 创建 (聊天上限)：创建新的聊天室；默认聊天上限为 1000\n"
            "罗德岛聊天 绑定 角色名：绑定一个角色；不绑定则使用 群昵称\n"
            "角色名或群昵称可通过加上‘#序号’选择该角色其他头像，例如：德克萨斯#2 可选择精二头像\n"
            "罗德岛聊天 开始：开始记录聊天内容；输入‘$结束‘或’$取消’结束记录\n"
            "罗德岛聊天 重置：重置聊天室"
        ),
    )


@alcommand(closure, private=False)
@assign("reset")
async def _reset(app: Ariadne, sender: Group):
    store.end(str(sender.id))
    if sender.id in rooms:
        rooms.remove(sender.id)
    return await app.send_message(sender, "[ClosureTalk] 重置完毕")


@alcommand(closure, private=False)
@assign("bind")
async def _bind(app: Ariadne, sender: Group, target: Member, name: Match[str]):
    try:
        if char := store.add_char(str(sender.id), target.id, name.result):
            return await app.send_message(sender, f"[ClosureTalk] 绑定成功: {char.id}")
        return await app.send_message(sender, "[ClosureTalk] 未找到角色，使用成员头像")
    except SessionNotExist as e:
        return await app.send_message(sender, str(e))


@alcommand(closure, private=False)
@assign("create")
async def _create(app: Ariadne, sender: Group, count: Match[int]):
    try:
        store.start(str(sender.id), count.result)
        return await app.send_message(sender, "[ClosureTalk] 创建房间成功")
    except SessionAlreadyExist as e:
        return await app.send_message(sender, str(e))


@alcommand(closure, private=False)
@assign("start")
async def _start(app: Ariadne, sender: Group, browser: PlaywrightBrowser):
    if str(sender.id) not in store.session:
        return await app.send_message(sender, "[ClosureTalk] 会话未存在")

    if sender.id in rooms:
        return
    rooms.append(sender.id)
    await app.send_message(sender, "[ClosureTalk] 记录开始！输入‘$结束‘或’$取消’结束记录")

    async def waiter(w_sender: Group, target: Member, message: MessageChain):
        if w_sender.id != sender.id:
            return
        if message.startswith("罗德岛聊天"):
            return
        if message.startswith("$结束") or message.startswith("$取消"):
            return False
        message = message.exclude(Face, MarketFace).merge()
        for index, elem in enumerate(message.content):
            if isinstance(elem, At) and not elem.representation:
                member = await app.get_member(w_sender, elem.target)
                elem.representation = member.name
        msg = str(message)
        if not msg:
            return
        try:
            try:
                store.add_content(msg, str(w_sender.id), target.id)
            except CharacterNotExist:
                store.add_char(str(w_sender.id), target.id, target.name)
                store.add_content(msg, str(w_sender.id), target.id)
        except (RecordMaxExceed, SessionNotExist):
            return False
        return True

    while True:
        wat = FunctionWaiter(waiter, [GroupMessage])
        res = await wat.wait(180, False)
        if res is None:
            continue
        if res is False:
            break

    file = cache_dir / f"{sender.id}.html"
    with file.open("w+", encoding="utf-8") as f:
        f.write(store.export(str(sender.id)))
    try:
        await app.send_message(sender, "[ClosureTalk] 记录结束，正在渲染中。。。")
        async with browser.page(
                viewport={"width": 500, "height": 1},
                device_scale_factor=1.5,
        ) as page:
            await page.goto(file.absolute().as_uri())
            # await page.set_content(store.export(str(sender.id)))
            img = await page.screenshot(type="jpeg", quality=80, full_page=True, scale="device")
            await app.send_message(sender, MessageChain(Image(data_bytes=img)))
    except Exception as e:
        await app.send_friend_message(bot.config.admin.master_id, f'{e}')
    finally:
        store.end(str(sender.id))
        rooms.remove(sender.id)


@listen(ActiveGroupMessage)
@priority(24)
async def _record_self(config: BotConfig, event: ActiveGroupMessage):
    gid = event.subject.id
    if gid not in rooms:
        return
    msg = str(event.message_chain)
    if msg.startswith("[ClosureTalk]"):
        return
    try:
        try:
            store.add_content(msg, str(gid), config.mirai.account)
        except CharacterNotExist:
            store.add_char(str(gid), config.mirai.account, config.bot_name)
            store.add_content(msg, str(gid), config.mirai.account)
    except RecordMaxExceed:
        return False
