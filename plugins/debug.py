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

from config import bot_config
from data import bot_data
from utils.simple_permission import require_admin

saya = Saya.current()
channel = Channel.current()

debug = Alconna(
    "调试",
    Args["option":["群组", "用户"]:Empty],
    headers=bot_config.command_prefix,
    help_text="显示调试信息",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=debug, help_flag="reply")))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot_config.master_id)])
)
async def _(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    arp = result.result
    mds = f"当前共加载模块：{len(saya.channels)}个\n已禁用模块：{bot_config.disabled_plugins}"
    groups_debug = f"当前共加入群：{len(bot_data.groups)}个"
    users_debug = f"当前共有：{len(bot_data.users)}人参与签到"
    if arp.option is None:
        return await app.sendMessage(sender, MessageChain.create(f"{mds}\n{groups_debug}\n{users_debug}"))
    elif arp.option == "群组":
        return await app.sendMessage(sender, MessageChain.create(f"{mds}\n{groups_debug}"))
    elif arp.option == "用户":
        return await app.sendMessage(sender, MessageChain.create(f"{mds}\n{users_debug}"))
