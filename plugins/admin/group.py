from typing import NamedTuple

from app import RaianBotInterface
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.event.mirai import BotLeaveEventDisband, BotLeaveEventKick, BotJoinGroupEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model.relationship import Group
from graiax.shortcut.saya import listen, priority
from ..config.admin import AdminConfig


class mute(NamedTuple):
    rest_count: int


@listen(GroupMessage)
@priority(7)
async def _init_g(app: Ariadne, group: Group, interface: RaianBotInterface):
    data = interface.data
    config = interface.config
    if not data.exist(group.id):
        data.add_group(group.id)
        data.cache["all_joined_group"].append(group.id)
        return await app.send_friend_message(
            config.admin.master_id, MessageChain(f"{group.name} 初始配置化完成")
        )


@listen(BotLeaveEventKick)
@priority(13)
async def get_kicked(app: Ariadne, event: BotLeaveEventKick, interface: RaianBotInterface):
    data = interface.data
    config = interface.config
    if event.group.id in data.cache["all_joined_group"]:
        data.cache["all_joined_group"].remove(event.group.id)
    if data.exist(event.group.id):
        data.remove_group(event.group.id)
    data.cache["blacklist"].append(event.group.id)
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(
            "收到被踢出群聊事件",
            f"\n群号：{event.group.id}",
            f"\n群名：{event.group.name}",
            f"\n已添加至黑名单",
        ),
    )


@listen(BotLeaveEventDisband)
@priority(13)
async def handle_disband(app: Ariadne, event: BotLeaveEventDisband, interface: RaianBotInterface):
    data = interface.data
    config = interface.config
    if event.group.id in data.cache["all_joined_group"]:
        data.cache["all_joined_group"].remove(event.group.id)
    if data.exist(event.group.id):
        data.remove_group(event.group.id)
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(
            "收到群聊解散事件", f"\n群号：{event.group.id}", f"\n群名：{event.group.name}"
        ),
    )


@listen(BotJoinGroupEvent)
async def get_join_group(app: Ariadne, group: Group, interface: RaianBotInterface):
    """
    收到入群事件
    """
    config = interface.config
    data = interface.data
    member_count = len(await app.get_member_list(group))
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(
            "收到加入群聊事件",
            f"\n群号：{group.id}",
            f"\n群名：{group.name}",
            f"\n群人数：{member_count}",
        ),
    )
    await app.send_group_message(
        group.id,
        MessageChain(
            f"我是 {config.admin.master_name} 的机器人 {(await app.get_bot_profile()).nickname}\n",
            f"如果有需要可以联系主人{config.admin.master_name}({config.admin.master_id})，\n",
            f"尝试发送 {config.command_prefix[0]}帮助 以查看功能列表\n",
            "项目地址：https://github.com/RF-Tar-Railt/RaianBot\n",
            "赞助（爱发电）：https://afdian.net/@rf_tar_railt\n"
            "机器人交流群：122680593",
        ),
    )
    if data.exist(group.id) and (count := data.get_group(group.id).get(mute)):
        admin: "AdminConfig" = interface.config.plugin.get(AdminConfig)
        await app.send_group_message(
            group.id,
            MessageChain(
                f"检测到机器人曾在该群被禁言 {admin.mute_max - count.rest_count}次\n"
                f"达到5次后机器人将不再接收入群申请\n"
                f"5次以上后群主或管理员需要将禁言理由发送给机器人, 经过审核后可继续使用机器人\n"
            ),
        )
    if group.id in data.cache.get('blacklist', []):
        await app.send_group_message(
            group.id,
            MessageChain(
                f"检测到机器人曾被踢出该群聊\n"
                f"该群已列入机器人黑名单，禁用大部分功能\n"
                f"恢复使用请管理员输入命令 '{config.command_prefix[0]}群组 黑名单 解除' "
            ),
        )
