import random
import re
from datetime import datetime
from pathlib import Path

import ujson
from arclet.alconna import command_manager
from arclet.alconna.graia.dispatcher import output_cache, result_cache
from avilla.core import Context, MessageReceived, Notice, Picture, Text
from avilla.elizabeth.account import ElizabethAccount
from graia.amnesia.builtins.aiohttp import AiohttpClientService
from graia.broadcast.exceptions import PropagationCancelled
from graia.saya.builtins.broadcast.shortcut import listen, priority

from app.config import BotConfig
from app.core import RaianBotService
from app.shortcut import accessable, exclusive, is_qqapi_group, record
from library.rand import random_pick_small
from library.tencentcloud import TencentCloudApi

from .config import DialogConfig

bot = RaianBotService.current()

json_filename = "assets/data/dialog_templates.json"
with open(json_filename, encoding="UTF-8") as f_obj:
    dialog_templates = ujson.load(f_obj)
config: DialogConfig = bot.config.plugin.get(DialogConfig)

api = None
if config.tencent:
    api = TencentCloudApi(
        bot.config.platform.tencentcloud_secret_id,
        bot.config.platform.tencentcloud_secret_key,
        proxy=bot.config.proxy,
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


async def random_ai(ctx: Context, msg: str, aio: AiohttpClientService, conf: BotConfig, **kwargs: float):
    session = f"{ctx.client}"
    if not config.tencent and not config.gpt_api:
        return
    ai_url = config.gpt_api
    rand = random_pick_small([1, 2, 3], [0.05, kwargs.get("tx", 0.45), kwargs.get("gpt", 0.5)])
    if rand == 3 and ai_url:
        async with aio.session.get(ai_url, params={"text": msg, "session": f"{conf.name}/{session}"}) as resp:
            return "".join((await resp.json())["result"])
    if (rand == 2 or not ai_url) and api:
        reply = await api.chat(
            msg,
            session,
            bot.config.platform.tencentcloud_tbp_bot_id,
            bot.config.platform.tencentcloud_tbp_bot_env,
            conf.name,
        )
        return reply or error_handle(msg)
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
):
    """依据语料进行匹配回复"""
    mid = f"{event.message.id}@{ctx.account.route}"
    for cache in result_cache.values():
        if mid in cache and ((res := cache[mid].result()) and res.result.matched):
            raise PropagationCancelled
    for cache in output_cache.values():
        if mid in cache:
            raise PropagationCancelled
    content = str(event.message.content.include(Text)).lstrip()
    if not content.startswith(conf.name):
        return
    if content == conf.name:
        rand_str = random.choice(dialog_templates["default"])
    else:
        content = content[len(conf.name) :].lstrip()
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
            rand_str = await random_ai(ctx, content[:120], aio, conf, gpt=0.6, tx=0.35)
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
        rand_str = await random_ai(ctx, content[:120], aio, conf, gpt=0.4, tx=0.55)
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
):
    """真AI对话功能, 通过@机器人或者回复机器人来触发，机器人也会有几率自动对话"""
    mid = f"{event.message.id}@{ctx.account.route}"
    for cache in result_cache.values():
        if mid in cache and ((res := cache[mid].result()) and res.result.matched):
            raise PropagationCancelled
    for cache in output_cache.values():
        if mid in cache:
            raise PropagationCancelled
    content = str(event.message.content.include(Text)).lstrip()
    if not content or content == conf.name:
        return
    names = [command_manager._command_part(name)[1] for name in command_manager.all_command_raw_help()]
    if content.removeprefix(conf.name).split()[0] in names:
        raise PropagationCancelled
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        reply = await random_ai(ctx, content[:120], aio, conf, gpt=0.55, tx=0.4)
        if reply:
            await ctx.scene.send_message(reply, reply=None if is_qqapi_group(ctx) else event.message)
        return
    if is_qqapi_group(ctx):
        reply = await random_ai(ctx, content[:120], aio, conf, gpt=0.45, tx=0.55)
        if reply:
            await ctx.scene.send_message(reply)
        return
    if (
        isinstance(event.message.content[0], Notice)
        and event.message.content.get_first(Notice).target.last_value == ctx.account.route.last_value
    ):
        reply = await random_ai(ctx, content[:120], aio, conf, gpt=0.55, tx=0.45)
        if reply:
            await ctx.scene.send_message(reply, reply=event.message)
        return
    if not isinstance(ctx.account, ElizabethAccount):
        return
    for elem in bot.config.command.headers:
        if isinstance(elem, str):
            content = content.replace(elem, "", 1)
    if random.randint(0, 2000) == datetime.now().microsecond // 5000:
        reply = await random_ai(ctx, content[:120], aio, conf, gpt=0.55, tx=0.45)
        if reply:
            await ctx.scene.send_message(reply, reply=event.message)
