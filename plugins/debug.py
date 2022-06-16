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
saya = bot.saya
channel = Channel.current()

debug = Alconna(
    "调试",
    Args["option", ["群组", "用户"], Empty],
    headers=bot.config.command_prefix,
    help_text="显示调试信息",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=debug, help_flag="reply")))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot.config.master_id)])
)
async def _(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    arp = result.result
    mds = f"当前共加载模块：{len(saya.channels)}个\n已禁用模块：{bot.config.disabled_plugins}"
    groups_debug = f"当前共加入群：{len(bot.data.groups)}个"
    users_debug = f"当前共有：{len(bot.data.users)}人参与签到"
    if arp.option is None:
        return await app.send_message(sender, MessageChain(f"{mds}\n{groups_debug}\n{users_debug}"))
    elif arp.option == "群组":
        return await app.send_message(sender, MessageChain(f"{mds}\n{groups_debug}"))
    elif arp.option == "用户":
        return await app.send_message(sender, MessageChain(f"{mds}\n{users_debug}"))
