from typing import Union
from arclet.alconna import Args
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.ariadne.message.element import Image
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend, Member
from graia.ariadne.app import Ariadne

from config import bot_config
from data import bot_data
from modules.gacha.arknights import GArknights

channel = Channel.current()

draw = Alconna(
    "(抽卡|寻访)", Args["count":int:1],
    headers=bot_config.command_prefix,
    help_text=f"模拟方舟寻访 Example: {bot_config.command_prefix[0]}抽卡 300;",
)

file = "data/static/gacha_arknights.json"


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=draw, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def draw(
        app: Ariadne,
        sender: Union[Group, Friend],
        target: Union[Friend, Member],
        result: AlconnaProperty
):
    arp = result.result
    if bot_data.exist(target.id):
        user = bot_data.get_user(target.id)
        if not user.additional.get('gacha_proba'):
            user.additional['gacha_proba'] = {'arknights': [0, 2]}
        elif not user.additional['gacha_proba'].get('arknights'):
            user.additional['gacha_proba']['arknights'] = [0, 2]
        six_statis, six_per = user.additional['gacha_proba']['arknights']
        gacha = GArknights(file=file, six_per=six_per, six_statis=six_statis)
        data = gacha.gacha(arp.count)
        user.additional['gacha_proba']['arknights'] = [gacha.six_statis, gacha.six_per]
        bot_data.update_user(user)
    else:
        gacha = GArknights(file=file)
        data = gacha.gacha(arp.count)
    return await app.sendMessage(sender, MessageChain.create(Image(data_bytes=data)))
