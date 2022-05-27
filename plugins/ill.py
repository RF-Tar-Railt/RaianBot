from typing import Union
import json
import random
from arclet.alconna import Args, Empty, Option
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.ariadne.message.element import At
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from app import RaianMain

bot = RaianMain.current()
channel = Channel.current()

json_filename = "assets/data/ill_templates.json"
with open(json_filename, 'r', encoding='UTF-8') as f_obj:
    ill_templates = json.load(f_obj)['templates']

ill = Alconna(
    "发病", Args["name":[str, At]:Empty],
    headers=bot.config.command_prefix,
    options=[
        Option("模板", Args["template":list(ill_templates.keys())], help_text="指定发病模板")
    ],
    help_text=f"生成一段模板文字 Usage: 若不指定模板则会随机挑选一个; Example: {bot.config.command_prefix[0]}发病 老公;",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=ill, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def test2(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    event = result.source
    arp = result.result
    if arp.name:
        if isinstance(arp.name, At):
            target = arp.name.display
            if not target:
                target = (await app.getUserProfile(arp.name.target)).nickname
        else:
            target = arp.name
    elif isinstance(event.sender, Friend):
        target = event.sender.nickname
    else:
        target = event.sender.name
    if arp.find("模板"):
        template = ill_templates[arp.query("模板.template")]
    else:
        template = random.choice(list(ill_templates.values()))
    return await app.sendMessage(sender, MessageChain.create(template.format(target=target)))
