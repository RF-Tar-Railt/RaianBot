import ujson
import random
import re
from datetime import datetime
from pathlib import Path
from io import BytesIO
from PIL import Image as Img
from arclet.alconna.graia import startswith, endswith, success_record
from arclet.alconna import command_manager
from graia.ariadne.message.element import Plain, Voice, Image, Source, At, Face, Quote
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.app import Ariadne
from graia.ariadne.model import Friend, Group
from graia.ariadne.util.saya import listen, priority, dispatch
from graia.ariadne.util.cooldown import CoolDown
from graia.broadcast.exceptions import PropagationCancelled

from app import RaianBotService, record, Sender, Target
from library.aiml.entry import AIML
from library.translate import TencentTrans, YoudaoTrans
from plugins.config.dialog import DialogConfig

bot = RaianBotService.current()

json_filename = "assets/data/dialog_templates.json"
with open(json_filename, 'r', encoding='UTF-8') as f_obj:
    dialog_templates = ujson.load(f_obj)['templates']
trans = (
    TencentTrans(
        bot.config.tencent.secret_id, bot.config.tencent.secret_key
    ) if bot.config.plugin.get(DialogConfig).tencent else
    YoudaoTrans()
)
aiml = AIML(
    trans,
    name=f" {bot.config.bot_name}",
    gender=" girl",
    mother=" Arclet",
    father=" RF-Tar-Railt",
    phylum=" Robot",
    master=f" {bot.config.admin.master_name}",
    botmaster=" Master",
    birth=" 2004-02-02",
    birthplace=" Terra",
    location=" Rhodes Island",
    age=" 18",
    kingdom=" your heart",
    religion=" Atheists",
    family=" Railt's",
    order=" Nihilian"
)

aiml_files = "assets/data/alice"
aiml_brain = f"{bot.config.cache_dir}/plugins/aiml_brain.brn"
aiml.load_aiml(aiml_files, aiml_brain)
nickname = bot.config.plugin.get(DialogConfig).nickname.strip()
if not nickname:
    nickname = bot.config.bot_name


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
        name = rand_str.split('$')[-1]
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
            base = Img.open(BytesIO(await resp.content.read())).resize(
                size, Img.Resampling.LANCZOS
            )
        cover.thumbnail(size)
        base.paste(cover, (0, 0), cover)
        data = BytesIO()
        base.save(data, format='JPEG', quality=90, qtables="web_high")
        return Image(data_bytes=data.getvalue())
    else:
        name = rand_str.split('$')[-1]
        path = Path(f"assets/image/{name}")
        return Image(data_bytes=path.read_bytes()) if path.exists() else name


@listen(GroupMessage, FriendMessage)
@startswith(nickname, bind="message")
@priority(17)
@record("dialog")
async def smatch(app: Ariadne, target: Target, sender: Sender, message: MessageChain):
    """依据语料进行匹配回复"""
    if not isinstance(sender, Group) and sender.id == bot.config.mirai.account:
        return
    cmds = [i.name for i in command_manager.get_commands()]
    if msg := str(message.include(Plain)).strip():
        if len(success_record):
            success_record.clear()
            raise PropagationCancelled
        for n in cmds:
            if re.search(f'.*{n}.*', msg):
                raise PropagationCancelled
        for key, value in dialog_templates['content'].items():
            if re.match(f".*?{key}$", msg):
                rand_str = random.sample(value, 1)[0]
                if rand_str.startswith("#voice"):
                    rand_str = await voice(rand_str)
                elif rand_str.startswith("#image"):
                    rand_str = await image(rand_str, target)
                break
        else:
            if random.randint(1, 100) > 50 and (ai_url := bot.config.plugin.get(DialogConfig).gpt_api):
                id_ = f"g{sender.id}" if isinstance(sender, Group) else f"f{sender.id}"
                async with app.service.client_session.get(
                        ai_url, params={"text": msg[:120], "session": f"{bot.config.bot_name}/{id_}"}
                ) as resp:
                    rand_str = ''.join((await resp.json())["result"])
            else:
                rand_str = await aiml.chat(message=msg, session_id=target.id)
    else:
        rand_str = random.sample(dialog_templates['default'], 1)[0]
    if rand_str:  # noqa
        await app.send_message(sender, MessageChain(rand_str))  # noqa
        raise PropagationCancelled


@listen(GroupMessage, FriendMessage)
@endswith(nickname, bind="message")
@priority(17)
@record("dialog")
async def ematch(app: Ariadne, target: Target, sender: Sender, message: MessageChain):
    """依据语料进行匹配回复"""
    if not isinstance(sender, Group) and sender.id == bot.config.mirai.account:
        return
    if msg := str(message.include(Plain)).strip():
        for key, value in dialog_templates['content'].items():
            if re.match(f"^{key}.*?", msg):
                rand_str = random.sample(value, 1)[0]
                if rand_str.startswith("#voice"):
                    rand_str = await voice(rand_str)
                elif rand_str.startswith("#image"):
                    rand_str = await image(rand_str, target)
                break
        else:
            if random.randint(1, 100) > 50 and (ai_url := bot.config.plugin.get(DialogConfig).gpt_api):
                id_ = f"g{sender.id}" if isinstance(sender, Group) else f"f{sender.id}"
                async with app.service.client_session.get(
                        ai_url, params={"text": msg[:120], "session": f"{bot.config.bot_name}/{id_}"}
                ) as resp:
                    rand_str = ''.join((await resp.json())["result"])
            else:
                rand_str = await aiml.chat(message=msg, session_id=target.id)
    else:
        rand_str = random.sample(dialog_templates['default'], 1)[0]
    if rand_str:  # noqa
        await app.send_message(sender, MessageChain(rand_str))  # noqa
        raise PropagationCancelled


@listen(GroupMessage, FriendMessage)
@priority(18)
@dispatch(CoolDown(0.1))
@record("ai")
async def aitalk(app: Ariadne, target: Target, sender: Sender, message: MessageChain, source: Source):
    """真AI对话功能, 通过@机器人或者回复机器人来触发，机器人也会有几率自动对话"""
    if not isinstance(sender, Group) and sender.id == bot.config.mirai.account:
        return
    id_ = f"g{sender.id}" if isinstance(sender, Group) else f"f{sender.id}"
    cmds = [i.name for i in command_manager.get_commands()]
    for n in cmds:
        if re.search(f'.*{n}.*', str(message)):
            raise PropagationCancelled
    if not (ai_url := bot.config.plugin.get(DialogConfig).gpt_api):
        return
    if isinstance(target, Friend) or (message.has(At) and message.get_first(At).target == bot.config.mirai.account) or (
            message.has(Quote) and message.get_first(Quote).sender_id == bot.config.mirai.account
    ):
        async with app.service.client_session.get(
                ai_url, params={
                    "text": str(message.include(Plain, Face))[:120],
                    "session": f"{bot.config.bot_name}/{id_}"
                }
        ) as resp:
            reply = "".join((await resp.json())["result"])
        await app.send_message(sender, reply, quote=False if isinstance(target, Friend) else source)
        return
    for elem in bot.config.command_prefix:
        message = message.replace(elem, "")
    msg = str(message.include(Plain, Face))
    if len(msg) > 100:
        return
    if random.randint(0, 2000) == datetime.now().microsecond // 5000:
        async with app.service.client_session.get(
                ai_url, params={"text": msg[:120], "session": f"{bot.config.bot_name}/{id_}"}
        ) as resp:
            reply = (await resp.json())["result"]
        return await app.send_message(sender, reply, quote=source)
