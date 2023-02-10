import asyncio
import random
import time
from graiax.shortcut.saya import listen
from arclet.alconna.graia import startswith
from graia.ariadne import Ariadne
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.model.relationship import Friend
from graia.ariadne.message.chain import MessageChain
from app import record, RaianBotInterface, permission

from ..config.admin import AdminConfig


@listen(FriendMessage)
@record("broadcast")
@permission("master")
@startswith("公告:")
async def announcement(
    app: Ariadne, friend: Friend, message: MessageChain, interface: RaianBotInterface
):
    """公告广播功能"""
    msg = message.as_sendable()
    ft = time.time()
    data = interface.data
    admin: "AdminConfig" = interface.base_config.plugin.get(AdminConfig)
    group_list = await app.get_group_list()
    for group in group_list:
        if not data.exist(group.id):
            continue
        if "broadcast" in data.get_group(group.id).disabled or data.get_group(group.id).in_blacklist:
            continue
        try:
            await app.send_group_message(
                group.id, MessageChain(f"{admin.announcement_title}\n") + msg
            )
        except Exception as err:
            await app.send_friend_message(
                friend, MessageChain(f"{group.id} 的公告发送失败\n{err}")
            )
        await asyncio.sleep(random.uniform(5, 7))
    tt = time.time()
    await app.send_friend_message(friend, MessageChain(f"群发已完成，耗时 {tt - ft:.6f} 秒"))
