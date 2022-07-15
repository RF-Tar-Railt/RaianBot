import ujson
import random
import re
from pathlib import Path
from io import BytesIO
from PIL import Image as Img
from arclet.alconna.analysis.base import analyse_header
from arclet.alconna.graia.dispatcher import success_record
from graia.ariadne.message.element import Plain, Voice, Image
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.app import Ariadne
from graia.ariadne.util.saya import listen, priority
from graia.broadcast.exceptions import PropagationCancelled

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
    if res := analyse_header(bot.config.command_prefix, "{content}?", message, raise_exception=False):
        for elem in bot.config.command_prefix:
            message = message.replace(elem, "")
        msg = str(message.include(Plain))
        content = res['content']
        if not content and not msg:
            rand_str = random.sample(dialog_templates['default'], 1)[0]
        else:
            if content and len(success_record) and re.match(
                re.sub(r"\{[^{}]*}", "(.*?)", success_record.pop()),
                content
            ):
                return
            plain = False
            voice = False
            image = False
            for key, value in dialog_templates['plain'].items():
                if re.match(f".*?{key}$", msg):
                    rand_str = random.sample(value, 1)[0]
                    plain = True
                    break
            if not plain:
                for key, value in dialog_templates['voice'].items():
                    if re.match(f".*?{key}$", msg):
                        rand_str = random.sample(value, 1)[0]
                        rand_str = Voice(data_bytes=Path(f"assets/voice/{rand_str}").read_bytes())
                        voice = True
                        break

            if not plain and not voice:
                for key, value in dialog_templates['image'].items():
                    if re.match(f".*?{key}$", msg):
                        rand_str = random.sample(value, 1)[0]
                        if rand_str.startswith("^"):
                            mode, file = rand_str.split("$", 1)
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
                            rand_str = Image(data_bytes=Path(f"assets/image/{rand_str}").read_bytes())
                        image = True
                        break
                if not image:
                    rand_str = await aiml.chat(message=msg, session_id=target.id)
        if rand_str:  # noqa
            await app.send_message(sender, MessageChain(rand_str))  # noqa
            raise PropagationCancelled
    return
