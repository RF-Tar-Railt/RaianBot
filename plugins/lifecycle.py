import asyncio
from typing import Union
from arclet.alconna import Args, Empty
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya import Channel, Saya
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from app import RaianMain
from utils.control import require_admin

bot = RaianMain.current()
saya = Saya.current()
channel = Channel.current()

shutdown = Alconna(
    "关机",
    Args["time":int:0],
    headers=bot.config.command_prefix,
    help_text="关闭机器人",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=shutdown, help_flag="reply")))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot.config.master_id, include_ids=True)])
)
async def _(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    await app.sendMessage(sender, MessageChain.create("正在关机。。。"))
    await asyncio.sleep(result.result.time)
    await bot.stop()
