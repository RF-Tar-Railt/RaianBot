from typing import Union
from arclet.alconna import Args, Empty
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, At
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from app import RaianMain
from modules.arknights.random import RandomOperator
from utils.generate_img import create_image
from utils.control import require_function

bot = RaianMain.current()
channel = Channel.current()

random_ope = Alconna(
    "测试干员", Args["name", [str, At], Empty],
    headers=bot.config.command_prefix,
    help_text=f"依据名字测试你会是什么干员 Example: {bot.config.command_prefix[0]}测试干员 海猫;",
)


@bot.data.record("随机干员")
@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=random_ope, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage], decorators=[require_function("随机干员")]))
async def test2(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    """依据名字随机生成干员"""
    event = result.source
    arp = result.result
    if arp.name:
        if isinstance(arp.name, At):
            target = arp.name.display
            if not target:
                target = (await app.getUserProfile(arp.name.target)).nickname
        else:
            target = arp.name
    else:
        target = event.sender.name
    return await app.send_message(
        sender, MessageChain(
            Image(data_bytes=(await create_image(RandomOperator().generate(target))))
        )
    )
