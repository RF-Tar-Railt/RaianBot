from typing import Union
from arclet.alconna import Args, Empty, Option, command_manager
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.ariadne.message.element import Image
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from app import RaianMain
from utils.generate_img import create_image

bot = RaianMain.current()
channel = Channel.current()

helping = Alconna(
    "帮助", Args["id", int, Empty],
    headers=bot.config.command_prefix,
    help_text=f"查看帮助",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=helping, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def test2(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    arp = result.result
    cmds = command_manager.get_commands()
    if not arp.id:
        text = command_manager.all_command_help(show_index=True) + (
            "\n========================================================"
            "\n所有功能均无需 @机器人本身"
            "\n想给点饭钱的话，这里有赞助链接：https://afdian.net/@rf_tar_railt"
            "\n更多功能待开发，如有特殊需求可以向 3165388245 询问"
        )
        return await app.send_message(sender, MessageChain(Image(data_bytes=await create_image(text, cut=120))))
    try:
        text = command_manager.command_help(cmds[arp.id].path)
        return await app.send_message(sender, MessageChain(Image(data_bytes=await create_image(text, cut=120))))
    except IndexError:
        return await app.send_message(sender, MessageChain("ID错误！"))
