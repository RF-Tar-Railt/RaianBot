from typing import Union
from arclet.alconna import Args, Empty
from arclet.alconna.graia import Alconna, AlconnaProperty
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, At
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.app import Ariadne

from app import Sender, record, command
from modules.arknights.random import RandomOperator
from utils.generate_img import create_image

random_ope = Alconna(
    "测试干员", Args["name", [str, At], Empty],
    help_text=f"依据名字测试你会是什么干员 Example: $测试干员 海猫;",
)


@record("随机干员")
@command(random_ope)
async def ro(app: Ariadne, sender: Sender, result: AlconnaProperty[Union[GroupMessage, FriendMessage]]):
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
