from typing import NamedTuple

from app import RaianBotInterface
from graia.ariadne import Ariadne
from graia.ariadne.event.mirai import BotInvitedJoinGroupRequestEvent, NewFriendRequestEvent
from graia.ariadne.message.chain import MessageChain
from graiax.shortcut.saya import listen


class mute(NamedTuple):
    rest_count: int


@listen(NewFriendRequestEvent)
async def get_friend_accept(app: Ariadne, event: NewFriendRequestEvent, interface: RaianBotInterface):
    """
    收到好友申请
    """
    config = interface.config
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(
            "收到添加好友事件",
            f"\nQQ：{event.supplicant}",
            f"\n昵称：{event.nickname}",
            f"\n申请消息：{event.message.upper()}"
        ),
    )


@listen(BotInvitedJoinGroupRequestEvent)
async def bot_invite(app: Ariadne, event: BotInvitedJoinGroupRequestEvent, interface: RaianBotInterface):
    """
    被邀请入群
    """
    config = interface.config
    data = interface.data
    friend_list = await app.get_friend_list()
    if event.supplicant in map(lambda x: x.id, friend_list):
        await app.send_friend_message(
            config.admin.master_id,
            MessageChain(
                "收到邀请入群事件",
                f"\n邀请者：{event.supplicant} | {event.nickname}",
                f"\n群号：{event.source_group}",
                f"\n群名：{event.group_name}",
            ),
        )
        if data.exist(event.source_group) and data.get_group(event.source_group).get(mute, mute(1)).rest_count < 1:
            await event.reject("")
            return await app.send_friend_message(
                event.supplicant,
                MessageChain(f"该群被禁言次数达到上限, 已拒绝申请\n" f"请联系群主或管理员向机器人报备禁言理由"),
            )
        await event.accept("")
        return await app.send_friend_message(
            event.supplicant,
            MessageChain(
                f"{'该群已在黑名单中, 请告知管理员使用群管功能解除黑名单' if event.source_group in data.cache.setdefault('blacklist', {}) else 'accepted.'}"
            ),
        )
    return await event.reject("请先加机器人好友")
