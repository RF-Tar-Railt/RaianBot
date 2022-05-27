from typing import Union
import json
import random
import re
from arclet.alconna.analysis.base import analyse_header
from arclet.alconna.graia import AlconnaDispatcher
from graia.ariadne.message.element import Plain
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend, Member
from graia.ariadne.app import Ariadne
from graia.broadcast.exceptions import PropagationCancelled

from app import RaianMain
from modules.aiml.entry import AIML
from modules.translate import TencentTrans

bot = RaianMain.current()
channel = Channel.current()

json_filename = "assets/data/dialog_templates.json"
with open(json_filename, 'r', encoding='UTF-8') as f_obj:
    dialog_templates = json.load(f_obj)['templates']

aiml = AIML(
    TencentTrans(
        bot.config.plugin['dialog']['id'],
        bot.config.plugin['dialog']['key']
    ),
    name=" " + bot.config.bot_name,
    gender=" girl",
    mother=" Arclet",
    father=" RF-Tar-Railt",
    phylum=" Robot",
    master=" " + bot.config.master_name,
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


@channel.use(ListenerSchema([GroupMessage, FriendMessage], priority=17))
async def test2(app: Ariadne, target: Union[Member, Friend], sender: Union[Group, Friend], message: MessageChain):
    if res := analyse_header(bot.config.command_prefix, "{content}?", message, raise_exception=False):
        for elem in bot.config.command_prefix:
            message = message.replace(elem, "")
        msg = message.include(Plain).asDisplay()
        content = res['content']
        if not content and not msg:
            rand_str = random.sample(dialog_templates['default'], 1)[0]
        else:
            if content:
                if re.match(AlconnaDispatcher.success_hook, content):
                    AlconnaDispatcher.success_hook = 'None'
                    return
            action = False
            hate = False
            hentai = False
            for key, value in dialog_templates['action'].items():
                if re.match(f".*?{key}$", msg):
                    rand_str = random.sample(value, 1)[0]
                    hate = True
                    break
            if not action:
                for key, value in dialog_templates['hate'].items():
                    if re.match(f".*?{key}$", msg):
                        rand_str = random.sample(value, 1)[0]
                        hate = True
                        break
            if not hate:
                for key, value in dialog_templates['hentai'].items():
                    if re.match(f".*?{key}$", msg):
                        rand_str = random.sample(value, 1)[0]
                        hentai = True
                        break
            if not action and not hate and not hentai:  # TODO: 接入AI
                rand_str = await aiml.chat(message=msg, session_id=target.id)
        if rand_str:  # noqa
            await app.sendMessage(sender, MessageChain.create(rand_str))  # noqa
            raise PropagationCancelled
    return
