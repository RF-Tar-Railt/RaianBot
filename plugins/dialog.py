import random
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Optional

import ujson
from app import RaianBotInterface, RaianBotService, Sender, Target, exclusive, record, accessable
from arclet.alconna import command_manager
from arclet.alconna.graia import endswith, startswith, success_record
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Face, Image, Plain, Quote, Source, Voice
from graia.ariadne.model import Friend
from graia.ariadne.util.cooldown import CoolDown
from graia.broadcast.exceptions import PropagationCancelled
from graiax.shortcut.saya import listen, priority
from library.aiml.entry import AIML
from library.chat import TencentChatBot
from library.rand import random_pick_small
from library.translate import TencentTrans, YoudaoTrans
from PIL import Image as Img
from plugins.config.dialog import DialogConfig

bot = RaianBotService.current()
cd = CoolDown(0.1)
json_filename = "assets/data/dialog_templates.json"
with open(json_filename, "r", encoding="UTF-8") as f_obj:
    dialog_templates = ujson.load(f_obj)["templates"]
config: DialogConfig = bot.config.plugin.get(DialogConfig)
trans = TencentTrans(bot.config.tencent.secret_id, bot.config.tencent.secret_key) if config.tencent else YoudaoTrans()

nickname = config.nickname.strip()

tcbot = None
if config.tencent:
    tcbot = TencentChatBot(nickname, bot.config.tencent.secret_id, bot.config.tencent.secret_key)
aiml = None
if not tcbot and not config.gpt_api:
    aiml = AIML(
        trans,
        gender=" girl",
        mother=" Arclet",
        father=" RF-Tar-Railt",
        phylum=" Robot",
        botmaster=" Master",
        birth=" 2004-02-02",
        birthplace=" Terra",
        location=" Rhodes Island",
        age=" 18",
        kingdom=" your heart",
        religion=" Atheists",
        family=" Railt's",
        order=" Nihilian",
    )
    aiml_files = "assets/data/alice"
    aiml_brain = f"{bot.config.plugin_cache_dir / 'aiml_brain.brn'}"
    aiml.load_aiml(aiml_files, aiml_brain)


async def voice(string: str):
    rand_str = string.replace("#voice", "")
    if rand_str.startswith("^"):
        mode, sentence = rand_str.lstrip("^").split("$", 1)
        # if mode != 'jp':
        #     return sentence
        # with suppress(Exception):
        #     async with Ariadne.current().service.client_session.get(
        #         f"https://moegoe.azurewebsites.net/api/speak?text={sentence}&id={random.randint(0, 6)}",
        #         timeout=120,
        #     ) as resp:
        #         data = await resp.read()
        #     if data[:3] == b"400":
        #         return sentence
        #     res = await async_encode(data, ios_adaptive=True)
        #     return Voice(data_bytes=res)
        # return sentence
        return sentence
    else:
        name = rand_str.split("$")[-1]
        path = Path(f"assets/voice/{name}")
        return Voice(data_bytes=path.read_bytes()) if path.exists() else name


async def image(string: str, target: Target):
    rand_str = string.replace("#image", "")
    if rand_str.startswith("^"):
        mode, file = rand_str.lstrip("^").split("$", 1)
        if not mode.endswith("cover"):
            return Image(data_bytes=Path(f"assets/image/{file}").read_bytes())
        cover = Img.open(f"assets/image/{file}")
        size = cover.size
        async with Ariadne.current().service.client_session.get(
            f"https://q1.qlogo.cn/g?b=qq&nk={target.id}&s=640"
        ) as resp:
            base = Img.open(BytesIO(await resp.content.read())).resize(size, Img.Resampling.LANCZOS)
        cover.thumbnail(size)
        base.paste(cover, (0, 0), cover)
        data = BytesIO()
        base.save(data, format="JPEG", quality=90, qtables="web_high")
        return Image(data_bytes=data.getvalue())
    else:
        name = rand_str.split("$")[-1]
        path = Path(f"assets/image/{name}")
        return Image(data_bytes=path.read_bytes()) if path.exists() else name


def error_handle(t):
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


async def random_ai(app: Ariadne, sender: Sender, target: Target, msg: str, **kwargs: float):
    session = f"{app.account}-{sender.id}-{target.id}"
    interface = app.launch_manager.get_interface(RaianBotInterface)
    ai_url = config.gpt_api
    rand = random_pick_small([1, 2, 3], [0.1, kwargs.get("tx", 0.4), kwargs.get("gpt", 0.5)])
    if rand == 3 and ai_url:
        async with app.service.client_session.get(
            ai_url, params={"text": msg, "session": f"{interface.config.bot_name}/{session}"}
        ) as resp:
            return "".join((await resp.json())["result"])
    if rand == 2 and tcbot:
        if reply := tcbot.chat(msg):
            return reply
        if random.randint(1, 10) > 5:
            return error_handle(msg)
    if aiml:
        aiml.setting(name=interface.config.bot_name, master=interface.config.admin.master_name)
        return await aiml.chat(message=msg, session_id=session)
    return error_handle(msg)


@listen(GroupMessage, FriendMessage)
@startswith(nickname, bind="message")
@record("dialog")
@priority(20)
@exclusive
@accessable
async def smatch(app: Ariadne, target: Target, sender: Sender, message: MessageChain):
    """依据语料进行匹配回复"""
    cmds = [i.name for i in command_manager.get_commands()]
    if msg := str(message.include(Plain)).strip(" +"):
        if len(success_record):
            success_record.clear()
            raise PropagationCancelled
        for n in cmds:
            if re.search(f".*{n}.*", msg):
                raise PropagationCancelled
        for key, value in dialog_templates["content"].items():
            if re.match(f".*?{key}$", msg):
                rand_str = random.sample(value, 1)[0]
                if rand_str.startswith("#voice"):
                    rand_str = await voice(rand_str)
                elif rand_str.startswith("#image"):
                    rand_str = await image(rand_str, target)
                break
        else:
            rand_str = await random_ai(app, sender, target, msg[:120], gpt=0.6, tx=0.3)
    else:
        rand_str = random.sample(dialog_templates["default"], 1)[0]
    if rand_str:  # noqa
        await app.send_message(sender, MessageChain(rand_str))  # noqa
        raise PropagationCancelled


@listen(GroupMessage, FriendMessage)
@endswith(nickname, bind="message")
@record("dialog")
@priority(20)
@exclusive
@accessable
async def ematch(app: Ariadne, target: Target, sender: Sender, message: MessageChain):
    """依据语料进行匹配回复"""
    if msg := str(message.include(Plain)).strip(" +"):
        for key, value in dialog_templates["content"].items():
            if re.match(f"^{key}.*?", msg):
                rand_str = random.sample(value, 1)[0]
                if rand_str.startswith("#voice"):
                    rand_str = await voice(rand_str)
                elif rand_str.startswith("#image"):
                    rand_str = await image(rand_str, target)
                break
        else:
            rand_str = await random_ai(app, sender, target, msg[:120], gpt=0.4, tx=0.5)
    else:
        rand_str = random.sample(dialog_templates["default"], 1)[0]
    if rand_str:  # noqa
        await app.send_message(sender, MessageChain(rand_str))  # noqa
        raise PropagationCancelled


@listen(GroupMessage, FriendMessage)
@priority(22)
@record("ai")
@exclusive
@accessable
async def aitalk(
    app: Ariadne,
    target: Target,
    sender: Sender,
    message: MessageChain,
    source: Source,
    quote: Optional[Quote]
):
    """真AI对话功能, 通过@机器人或者回复机器人来触发，机器人也会有几率自动对话"""
    message = message.copy()
    if target.id == 2854196310:  # Q群管家
        return
    cmds = [i.name for i in command_manager.get_commands()]
    for n in cmds:
        if re.search(f".*{n}.*", str(message)):
            raise PropagationCancelled
    async with cd.trigger(sender.id, int) as res:
        if not res[1]:
            return
    if isinstance(target, Friend):
        reply = await random_ai(
            app, sender, target, str(message.include(Plain, Face)).strip(" +")[:120], gpt=0.5, tx=0.4
        )
        if reply:
            await app.send_message(sender, reply, quote=False if isinstance(target, Friend) else source)
        return
    if (message.has(At) and message.get_first(At).target == app.account) or (
        quote and quote.sender_id == app.account
    ):
        reply = await random_ai(
            app, sender, target, str(message.include(Plain, Face)).strip(" +")[:120], gpt=0.6, tx=0.3
        )
        if reply:
            await app.send_message(sender, reply, quote=False if isinstance(target, Friend) else source)
        return
    for elem in bot.config.command.headers:
        message = message.replace(elem, "")
    if random.randint(0, 2000) == datetime.now().microsecond // 5000:
        reply = await random_ai(
            app, sender, target, str(message.include(Plain, Face)).strip(" +")[:120], gpt=0.6, tx=0.3
        )
        if reply:
            return await app.send_message(sender, reply, quote=source)
