from typing import Union
import json
import random
import re
from pathlib import Path
from arclet.alconna.analysis.base import analyse_header
from arclet.alconna.graia.dispatcher import success_record
from graia.ariadne.message.element import Plain, Voice
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend, Member
from graia.ariadne.app import Ariadne
from graia.broadcast.exceptions import PropagationCancelled

from app import RaianMain
from modules.aiml.entry import AIML
from modules.translate import TencentTrans, YoudaoTrans
from utils.control import require_function

bot = RaianMain.current()
channel = Channel.current()

json_filename = "assets/data/dialog_templates.json"
with open(json_filename, 'r', encoding='UTF-8') as f_obj:
    dialog_templates = json.load(f_obj)['templates']

aiml = AIML(
    (
        TencentTrans(
            bot.config.plugin['dialog']['id'],
            bot.config.plugin['dialog']['key']
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


@bot.data.record("dialog")
@channel.use(ListenerSchema([GroupMessage, FriendMessage], priority=17, decorators=[require_function("dialog")]))
async def test2(app: Ariadne, target: Union[Member, Friend], sender: Union[Group, Friend], message: MessageChain):
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
            plains = dialog_templates['action'].copy()
            plains.update(dialog_templates['hate'])
            plains.update(dialog_templates['hentai'])
            for key, value in plains.items():
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

            if not voice:  # TODO: 接入AI
                rand_str = await aiml.chat(message=msg, session_id=target.id)
        if rand_str:  # noqa
            await app.send_message(sender, MessageChain(rand_str))  # noqa
            raise PropagationCancelled
    return
