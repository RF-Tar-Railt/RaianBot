from contextlib import suppress
from typing import NamedTuple

from app import RaianBotInterface, meta_export, permission
from arclet.alconna.graia import startswith
from graia.ariadne import Ariadne
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.exception import AccountNotFound, InvalidArgument, UnknownTarget
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model.relationship import Friend, Group, MemberPerm
from graiax.shortcut.saya import listen

from .event import AccountMuted
from ..config.admin import AdminConfig


class mute(NamedTuple):
    rest_count: int


meta_export(group_meta=[mute])


@listen(FriendMessage)
@permission("admin")
@startswith("解除群限制:", bind="message")
async def discard_mute(
    app: Ariadne, friend: Friend, message: MessageChain, interface: RaianBotInterface, admin: AdminConfig
):
    data = interface.data
    target = int(str(message))
    if not data.exist(target):
        return
    prof = data.get_group(target)
    prof.set(mute(admin.mute_max))
    data.update_group(prof)
    return await app.send_friend_message(friend, MessageChain("该群限制解除成功"))


@listen(AccountMuted)
async def handle_mute(app: Ariadne, group: Group, interface: RaianBotInterface):
    config = interface.config
    data = interface.data
    admin: "AdminConfig" = interface.base_config.plugin.get(AdminConfig)
    members = await app.get_member_list(group)
    prof = data.get_group(group.id)
    count = prof.get(mute, mute(admin.mute_max))
    if count.rest_count <= 0:
        return
    await app.quit_group(group)
    prof.set(mute(count.rest_count - 1))
    data.update_group(prof)
    friend_ids = [f.id for f in (await app.get_friend_list())]
    for ad in filter(
        lambda x: x.id in friend_ids and x.permission > MemberPerm.Member,
        members,
    ):
        with suppress(AccountNotFound, InvalidArgument, UnknownTarget):
            await app.send_friend_message(
                ad.id,
                MessageChain(
                    f"因机器人被禁言, 机器人已自动退出该群聊\n"
                    f"再禁言 {count} 次后机器人将不再自动接受该群的邀请入群申请\n"
                    f"到达 {admin.mute_max}次后需要群主或管理员向机器人报备禁言理由后才可接受邀请"
                ),
            )
    return await app.send_friend_message(
        config.admin.master_id,
        MessageChain(f"检测到在 {group} 中被禁言，已退出该群聊"),
    )
