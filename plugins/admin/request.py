from typing import NamedTuple

from app import RaianBotInterface
from arclet.alconna import Alconna, Args
from arclet.alconna.graia import alcommand, Match
from graia.ariadne import Ariadne
from graia.ariadne.event.mirai import BotInvitedJoinGroupRequestEvent, NewFriendRequestEvent
from graia.ariadne.message.chain import MessageChain
from graiax.shortcut.saya import listen
from graia.ariadne.model.relationship import Friend
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.util.interrupt import FunctionWaiter


class mute(NamedTuple):
    rest_count: int


@alcommand(Alconna("自动同意请求", Args["opt", {"on": True, "off": False, ...: True}]), guild=False)
async def auto_accept(app: Ariadne, sender: Friend, opt: Match[bool], interface: RaianBotInterface):
    if opt.result:
        await app.send_message(sender, "已开启自动同意请求")
        interface.data.cache["auto_accept"] = True
    else:
        await app.send_message(sender, "已关闭自动同意请求")
        interface.data.cache["auto_accept"] = False


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
    if interface.data.cache.get("auto_accept", False):
        await event.accept("同意请求")
        await app.send_friend_message(
            config.admin.master_id,
            "已自动同意请求"
        )
    else:
        async def waiter(sender: Friend, msg: MessageChain):
            if sender.id == config.admin.master_id:
                return str(msg)

        await app.send_friend_message(config.admin.master_id, "处理请求等待中")
        res = await FunctionWaiter(waiter, [FriendMessage], block_propagation=True).wait(120)
        if not res:
            await event.reject("管理员超时未回复，请尝试重新发送请求")
            await app.send_friend_message(
                config.admin.master_id,
                "因为超时已拒绝请求"
            )
            return
        if res in ("同意", "yes", "y", "ok", "好", "是", "同意请求"):
            await event.accept("同意请求")
            await app.send_friend_message(
                config.admin.master_id,
                "已同意请求"
            )
        else:
            await event.reject("拒绝请求")
            await app.send_friend_message(
                config.admin.master_id,
                "已拒绝请求"
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
        if interface.data.cache.get("auto_accept", False):
            await event.accept("已自动同意请求")
            await app.send_friend_message(
                config.admin.master_id,
                "已自动同意请求"
            )
            return await app.send_friend_message(
                event.supplicant,
                MessageChain(
                    f"{'该群已在黑名单中, 请告知管理员使用群管功能解除黑名单' if event.source_group in data.cache.setdefault('blacklist', {}) else 'accepted.'}"
                ),
            )
        async def waiter(sender: Friend, msg: MessageChain):
            if sender.id == config.admin.master_id:
                return str(msg)

        await app.send_friend_message(event.supplicant, "请等待机器人管理员处理该请求")
        await app.send_friend_message(config.admin.master_id, "处理请求等待中")
        res = await FunctionWaiter(waiter, [FriendMessage], block_propagation=True).wait(120)
        if not res:
            await event.reject("管理员超时未回复，请尝试重新发送请求")
            await app.send_friend_message(
                event.supplicant,
                "管理员超时未回复，请尝试重新发送请求"
            )
            await app.send_friend_message(
                config.admin.master_id,
                "因为超时已拒绝请求"
            )
            return
        if res in ("同意", "yes", "y", "ok", "好", "是", "同意请求"):
            await event.accept("已同意请求")
            await app.send_friend_message(
                config.admin.master_id,
                "已同意请求"
            )
            return await app.send_friend_message(
                event.supplicant,
                MessageChain(
                    f"{'该群已在黑名单中, 请告知管理员使用群管功能解除黑名单' if event.source_group in data.cache.setdefault('blacklist', {}) else 'accepted.'}"
                ),
            )
        else:
            await event.reject("拒绝请求")
            await app.send_friend_message(
                config.admin.master_id,
                "已拒绝请求"
            )
            return await app.send_friend_message(
                event.supplicant,
                "已拒绝请求"
            )
    return await event.reject("请先加机器人好友")
