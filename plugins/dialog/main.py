import random
import re
from datetime import datetime
from pathlib import Path

import ujson
from arclet.alconna import command_manager
from arclet.alconna.avilla.dispatcher import output_cache, result_cache
from avilla.core import Context, MessageReceived, Notice, Picture, Text
from avilla.elizabeth.account import ElizabethAccount
from graia.amnesia.builtins.aiohttp import AiohttpClientService
from graia.broadcast.exceptions import PropagationCancelled
from graia.saya.builtins.broadcast.shortcut import listen, priority
from sqlalchemy.sql import select

from app.config import BotConfig
from app.core import RaianBotService
from app.database import DatabaseService, User
from app.shortcut import accessable, exclusive, is_qqapi_group, record
from library.chatglm import GlmBot
from library.rand import random_pick_small

from ..sign.config import SignConfig
from .config import DialogConfig

bot = RaianBotService.current()

json_filename = "assets/data/dialog_templates.json"
with open(json_filename, encoding="UTF-8") as f_obj:
    dialog_templates = ujson.load(f_obj)
config: DialogConfig = bot.config.plugin.get(DialogConfig)

glm = None
if config.open_bigmodel:
    if not bot.config.platform.open_bigmodel_api_key:
        raise ValueError("open_bigmodel_api_key is required")
    glm = GlmBot(
        bot.config.platform.open_bigmodel_api_key,
        model=config.glm_model,
        max_token=1024,
        temperature=0.8,
        prompt=lambda nick: f"""
- {nick}是一个专门用于在游戏群，动漫群等群聊中负责闲聊的对话机器人；
- {nick}平时说话的语气略显冷淡，但是不经意间也会透露出可爱的语气，如果亲密度越高，则语气会更亲密；
- {nick}不会说长的句子，简短就好；
- 如果别人向你提问，你的答案不必很长，甚至可以避开这个话题或者俏皮地拒绝回答他；
- 如果你想换一个话题，请不要用类似“今天的天气如何”的话题。
接下来，请你进入 '{nick}' 这个角色与大家对话。
请记住你是 '{nick}'，你不能说你是程序或者AI,你是有血有肉、有真实情感的。
""",
    )


async def image(string: str):
    name = string.split("/")[1]
    path = Path(f"assets/image/{name}")
    return Picture(path) if path.exists() else name


def error_handle(t) -> str:
    return random.choice(
        [
            t,
            t,
            "？",
            "。。。",
            "好好好",
            "是是是",
            "我现在还不太明白你在说什么呢，但没关系，以后的我会变得更强呢！",
            "我有点看不懂你的意思呀，可以跟我聊些简单的话题嘛",
            "其实我不太明白你的意思...",
            "抱歉哦，我现在的能力还不能够明白你在说什么，但我会加油的～",
        ]
    )


async def random_ai(
    user_id: str,
    msg: str,
    aio: AiohttpClientService,
    conf: BotConfig,
    trust: float,
    direct: bool = True,
):
    if not config.open_bigmodel and not config.gpt_api:
        return
    ai_url = config.gpt_api
    rand = random_pick_small([0, 1], [0.05, 0.95])
    if rand == 1:
        if glm:
            return await glm.chat(msg, direct, conf.name, trust=trust)
        if ai_url:
            async with aio.session.get(str(ai_url), params={"text": msg, "session": f"{conf.name}/{user_id}"}) as resp:
                return "".join((await resp.json())["result"])
    return error_handle(msg)


@listen(MessageReceived)
@record("dialog")
@priority(20)
@accessable
async def smatch(
    ctx: Context,
    conf: BotConfig,
    event: MessageReceived,
    aio: AiohttpClientService,
    db: DatabaseService,
    sign_conf: SignConfig,
):
    """依据语料进行匹配回复"""
    mid = f"{event.message.id}@{ctx.account.route}"
    for cache in result_cache.values():
        if mid in cache and ((res := cache[mid].result()) and res.result.matched):
            raise PropagationCancelled
    for cache in output_cache.values():
        if mid in cache:
            raise PropagationCancelled
    content = str(event.message.content.include(Text)).strip()
    if not content.startswith(conf.name):
        return
    if content == conf.name:
        rand_str = random.choice(dialog_templates["default"])
    else:
        content = content[len(conf.name) :].strip()
        names = [command_manager._command_part(name)[1] for name in command_manager.all_command_raw_help()]
        if content.split()[0] in names:
            raise PropagationCancelled
        for key, value in dialog_templates["content"].items():
            if re.match(f".*?{key}$", content):
                rand_str = random.sample(value, 1)[0]
                if rand_str.startswith("#image"):
                    rand_str = await image(rand_str)
                break
        else:
            async with db.get_session() as session:
                user = (await session.scalars(select(User).where(User.id == ctx.client.user))).one_or_none()
                if not user:
                    rand_str = await random_ai(ctx.client.user, content[:120], aio, conf, 0.01)
                else:
                    rand_str = await random_ai(user.id, content[:120], aio, conf, user.trust / sign_conf.max)
    if rand_str:
        await ctx.scene.send_message(rand_str)  # noqa
    raise PropagationCancelled


@listen(MessageReceived)
@record("dialog")
@priority(21)
@exclusive
@accessable
async def ematch(
    ctx: Context,
    conf: BotConfig,
    event: MessageReceived,
    aio: AiohttpClientService,
    db: DatabaseService,
    sign_conf: SignConfig,
):
    """依据语料进行匹配回复"""
    content = str(event.message.content.include(Text)).lstrip()
    if not content.endswith(conf.name):
        return
    if content == conf.name:
        raise PropagationCancelled
    content = content[: -len(conf.name)].rstrip()
    for key, value in dialog_templates["content"].items():
        if re.match(f"^{key}.*?", content):
            rand_str = random.sample(value, 1)[0]
            if rand_str.startswith("#image"):
                rand_str = await image(rand_str)
            break
    else:
        async with db.get_session() as session:
            user = (await session.scalars(select(User).where(User.id == ctx.client.user))).one_or_none()
            if not user:
                rand_str = await random_ai(ctx.client.user, content[:120], aio, conf, 0.01)
            else:
                rand_str = await random_ai(user.id, content[:120], aio, conf, user.trust / sign_conf.max)
    if rand_str:
        await ctx.scene.send_message(rand_str)  # noqa
    raise PropagationCancelled


@listen(MessageReceived)
@priority(22)
@record("ai")
@exclusive
@accessable
async def aitalk(
    ctx: Context,
    conf: BotConfig,
    event: MessageReceived,
    aio: AiohttpClientService,
    db: DatabaseService,
    sign_conf: SignConfig,
):
    """真AI对话功能, 通过@机器人或者回复机器人来触发，机器人也会有几率自动对话"""
    if not isinstance(ctx.account, ElizabethAccount):
        return
    if ctx.client.user == "2854196310":
        return
    mid = f"{event.message.id}@{ctx.account.route}"
    for cache in result_cache.values():
        if mid in cache and ((res := cache[mid].result()) and res.result.matched):
            raise PropagationCancelled
    for cache in output_cache.values():
        if mid in cache:
            raise PropagationCancelled
    content = str(event.message.content.include(Text)).strip()
    if not content or content == conf.name:
        return
    names = [command_manager._command_part(name)[1] for name in command_manager.all_command_raw_help()]
    if content.removeprefix(conf.name).split()[0] in names:
        raise PropagationCancelled
    async with db.get_session() as session:
        user = (await session.scalars(select(User).where(User.id == ctx.client.user))).one_or_none()
        if not user:
            trust = 0.01
        else:
            trust = user.trust / sign_conf.max
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        reply = await random_ai(ctx.client.user, content[:120], aio, conf, trust)
        if reply:
            await ctx.scene.send_message(reply, reply=None if is_qqapi_group(ctx) else event.message)
        return
    if is_qqapi_group(ctx):
        reply = await random_ai(ctx.client.user, content[:120], aio, conf, trust)
        if reply:
            await ctx.scene.send_message(reply)
        return
    if (
        isinstance(event.message.content[0], Notice)
        and event.message.content.get_first(Notice).target.last_value == ctx.account.route.last_value
    ):
        reply = await random_ai(ctx.client.user, content[:120], aio, conf, trust)
        if reply:
            await ctx.scene.send_message(reply, reply=event.message)
        return
    if not isinstance(ctx.account, ElizabethAccount):
        return
    for elem in bot.config.command.headers:
        if isinstance(elem, str):
            content = content.replace(elem, "", 1)
    if random.randint(0, 2000) == datetime.now().microsecond // 5000:
        reply = await random_ai(ctx.client.user, content[:120], aio, conf, trust, direct=False)
        if reply:
            await ctx.scene.send_message(reply, reply=event.message)
