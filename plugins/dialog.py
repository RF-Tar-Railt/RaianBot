import ujson
import random
import re
from datetime import datetime
from pathlib import Path
from io import BytesIO
from PIL import Image as Img
from aiohttp import ClientSession, TCPConnector
from arclet.alconna.analysis.base import analyse_header, _DummyAnalyser
from arclet.alconna.graia.dispatcher import success_record
from graia.ariadne.message.element import Plain, Voice, Image, Source, At, Face, Quote
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.app import Ariadne
from graia.ariadne.util.saya import listen, priority, dispatch
from graia.ariadne.util.cooldown import CoolDown
from graia.broadcast.exceptions import PropagationCancelled
from graiax.silkcoder import async_encode

from app import RaianMain, record, Sender, Target
from modules.aiml.entry import AIML
from modules.translate import TencentTrans, YoudaoTrans

bot = RaianMain.current()

json_filename = "assets/data/dialog_templates.json"
with open(json_filename, 'r', encoding='UTF-8') as f_obj:
    dialog_templates = ujson.load(f_obj)['templates']

aiml = AIML(
    (
        TencentTrans(
            bot.config.plugin['dialog']['id'], bot.config.plugin['dialog']['key']
        ) if bot.config.plugin['dialog']['tencent'] else
        YoudaoTrans()
    ),
    name=f" {bot.config.bot_name}",
    gender=" girl",
    mother=" Arclet",
    father=" RF-Tar-Railt",
    phylum=" Robot",
    master=f" {bot.config.master_name}",
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


@record("dialog")
@priority(17)
@listen(GroupMessage, FriendMessage)
async def test2(app: Ariadne, target: Target, sender: Sender, message: MessageChain):
    """依据语料进行匹配回复"""
    _DummyAnalyser.filter_out = ["Source", "Quote", "File"]
    if res := analyse_header(bot.config.command_prefix, "{content}?", message, raise_exception=False):
        _DummyAnalyser.filter_out = []
        for elem in bot.config.command_prefix:
            message = message.replace(elem, "")
        msg = str(message.include(Plain))
        content = res['content']
        if not content and not msg:
            rand_str = random.sample(dialog_templates['default'], 1)[0]
        else:
            if content and len(success_record):
                success_record.clear()
                raise PropagationCancelled
            for key, value in dialog_templates['content'].items():
                if re.match(f".*?{key}$", msg):
                    rand_str = random.sample(value, 1)[0]
                    if rand_str.startswith("#voice"):
                        rand_str = rand_str.replace("#voice", "")
                        if rand_str.startswith("^"):
                            mode, sentence = rand_str.lstrip("^").split("$", 1)
                            if mode == 'jp':
                                async with ClientSession(connector=TCPConnector(limit=64, verify_ssl=False)) as session:
                                    try:
                                        async with session.post(
                                            "https://cloud.ai-j.jp/demo/aitalk2webapi_nop.php",
                                            data={"speaker_id": 1209, "text": sentence, "speed": 0.8, "pitch": 1.1},

                                        ) as resp:
                                            audio_name = (await resp.text())[47:-3]
                                        async with session.get(
                                            f"https://cloud.ai-j.jp/demo/tmp/{audio_name}"
                                        ) as resp:
                                            data = await resp.read()
                                        time = len(data) * 8 / 128000
                                        start = 3.8 if time > (3.1 if len(sentence) < 4 else 4.5) else 2.3
                                        res = await async_encode(data[int(start * 128000 / 8):], ios_adaptive=True)
                                        rand_str = Voice(data_bytes=res)
                                    except Exception:
                                        rand_str = sentence
                            else:
                                rand_str = sentence
                        else:
                            name = rand_str.split('$')[-1]
                            path = Path(f"assets/voice/{name}")
                            rand_str = Voice(data_bytes=path.read_bytes()) if path.exists() else name
                    elif rand_str.startswith("#image"):
                        rand_str = rand_str.replace("#image", "")
                        if rand_str.startswith("^"):
                            mode, file = rand_str.lstrip("^").split("$", 1)
                            if mode.endswith("cover"):
                                cover = Img.open(f"assets/image/{file}")
                                size = cover.size
                                async with app.service.client_session.get(
                                        f"https://q1.qlogo.cn/g?b=qq&nk={target.id}&s=640"
                                ) as resp:
                                    base = Img.open(BytesIO(await resp.content.read())).resize(
                                        size, Img.ANTIALIAS
                                    )
                                cover.thumbnail(size)
                                base.paste(cover, (0, 0), cover)
                                data = BytesIO()
                                base.save(data, format='JPEG', quality=90, qtables="web_high")
                                rand_str = Image(data_bytes=data.getvalue())
                            else:
                                rand_str = Image(data_bytes=Path(f"assets/image/{file}").read_bytes())
                        else:
                            name = rand_str.split('$')[-1]
                            path = Path(f"assets/image/{name}")
                            rand_str = Image(data_bytes=path.read_bytes()) if path.exists() else name
                    break
            else:
                rand_str = await aiml.chat(message=msg, session_id=target.id)
        if rand_str:  # noqa
            await app.send_message(sender, MessageChain(rand_str))  # noqa
            raise PropagationCancelled
    return


@record("ai", disable=True)
@priority(18)
@dispatch(CoolDown(0.1))
@listen(GroupMessage, FriendMessage)
async def test2(app: Ariadne, target: Target, sender: Sender, message: MessageChain, source: Source):
    """真AI对话功能"""
    if not (ai_url := bot.config.plugin['dialog']['ai_url']):
        return
    if (message.has(At) and message.get_first(At).target == bot.config.account) or (
        message.has(Quote) and message.get_first(Quote).sender_id == bot.config.account
    ):
        async with app.service.client_session.get(
            ai_url, params={
                "text": message.include(Plain, Face).display,
                "session": f"{bot.config.bot_name}/{target.id}"
            }
        ) as resp:
            reply = (await resp.json())["result"]
        return await app.send_message(sender, reply, quote=source)
    if analyse_header(bot.config.command_prefix, "{content}?", message, raise_exception=False):
        for elem in bot.config.command_prefix:
            message = message.replace(elem, "")
    msg = str(message.include(Plain, Face))
    if random.randint(0, 2000) == datetime.now().microsecond // 5000:
        async with app.service.client_session.get(
                ai_url, params={"text": msg, "session": f"{bot.config.bot_name}/{target.id}"}
        ) as resp:
            reply = (await resp.json())["result"]
        return await app.send_message(sender, reply, quote=source)
