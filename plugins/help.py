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
    "帮助", Args["id":int:Empty],
    headers=bot.config.command_prefix,
    options=[
        Option("page|-p", Args["page":int], help_text="指定页数", dest="index")
    ],
    help_text=f"查看帮助 Example: {bot.config.command_prefix[0]}帮助 page 1;",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=helping, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def test2(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    arp = result.result
    cmds = command_manager.get_commands()
    if not arp.id:
        page = arp.query("index.page", 0)
        text = command_manager.all_command_help(show_index=True, max_length=10, page=page)
        return await app.sendMessage(sender, MessageChain.create(Image(data_bytes=await create_image(text, cut=120))))
    try:
        text = command_manager.command_help(cmds[arp.id].path)
        return await app.sendMessage(sender, MessageChain.create(Image(data_bytes=await create_image(text, cut=120))))
    except IndexError:
        return await app.sendMessage(sender, MessageChain.create("ID错误！"))
