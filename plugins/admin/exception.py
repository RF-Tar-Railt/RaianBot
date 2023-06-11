from app import RaianBotInterface, create_image, permission, exclusive, Sender
from app.report import generate_reports
from graia.ariadne import Ariadne
from graia.ariadne.exception import AccountMuted, RemoteException
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.event.mirai import MemberJoinEvent, MemberLeaveEventQuit
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.model import MemberInfo
from graia.broadcast.builtin.event import ExceptionThrown, ExceptionThrowed
from graiax.shortcut.saya import listen, priority
from arclet.alconna.graia import startswith
from contextlib import suppress

from .event import AccountMuted as AccountMutedEvent


@listen(FriendMessage, GroupMessage)
@permission("admin")
@startswith("昵称还原")
@exclusive
async def nickname_restore(app: Ariadne, sender: Sender, interface: RaianBotInterface):
    for gid in interface.data.cache.get("$name_change", []):
        with suppress(Exception):
            await app.modify_member_info(
                app.account,
                MemberInfo(name=interface.base_config.command.headers[0]),
                gid
            )
    interface.data.cache.pop("$name_change", None)
    await app.send_message(sender, "已完成")



@listen(ExceptionThrown)
@priority(13)
async def report(app: Ariadne, event: ExceptionThrown, interface: RaianBotInterface):
    config = interface.config
    if isinstance(event.exception, AccountMuted) and isinstance(event.event, GroupMessage):
        for listener in app.broadcast.default_listener_generator(AccountMutedEvent):
            await listener.callable(app, event.event.sender.group, interface)
        return
    if isinstance(event.exception, RemoteException):
        msg = event.exception.args[1]['msg']
        if 'LIMITED_MESSAGING' in msg and isinstance(event.event, GroupMessage):
            await app.modify_member_info(
                app.account,
                MemberInfo(name=f"{interface.base_config.command.headers[0]} - 检测到机器人被风控，请暂停使用"),
                event.event.sender.group,
            )
            interface.data.cache.setdefault("$name_change", []).append(event.event.sender.group.id)
        elif 'GROUP_CHAT_LIMITED' in msg and isinstance(event.event, GroupMessage):
            await app.modify_member_info(
                app.account,
                MemberInfo(name=f"{interface.base_config.command.headers[0]} - 检测到该群存在发言限制，请暂停使用"),
                event.event.sender.group,
            )
            interface.data.cache.setdefault("$name_change", []).append(event.event.sender.group.id)
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(Image(data_bytes=await create_image("".join(generate_reports(event.exception))))),
    )


@listen(ExceptionThrowed)
@priority(13)
async def report(app: Ariadne, event: ExceptionThrowed, interface: RaianBotInterface):
    config = interface.config
    if isinstance(event.exception, AccountMuted) and isinstance(event.event, GroupMessage):
        for listener in app.broadcast.default_listener_generator(AccountMutedEvent):
            await listener.callable(app, event.event.sender.group, interface)
        return
    if isinstance(event.exception, RemoteException):
        msg = event.exception.args[1]['msg']
        if 'LIMITED_MESSAGING' in msg and isinstance(event.event, GroupMessage):
            await app.modify_member_info(
                app.account,
                MemberInfo(name=f"{interface.base_config.command.headers[0]} - 检测到机器人被风控，请暂停使用"),
                event.event.sender.group,
            )
            interface.data.cache.setdefault("$name_change", []).append(event.event.sender.group.id)
        elif 'GROUP_CHAT_LIMITED' in msg and isinstance(event.event, GroupMessage):
            await app.modify_member_info(
                app.account,
                MemberInfo(name=f"{interface.base_config.command.headers[0]} - 检测到该群存在发言限制，请暂停使用"),
                event.event.sender.group,
            )
            interface.data.cache.setdefault("$name_change", []).append(event.event.sender.group.id)
    tb = "".join(generate_reports(event.exception))
    tb = f"## 概览\n\n在处理 {event.event} 时出现如下问题:\n{tb}"
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(Image(data_bytes=await create_image(tb))),
    )
