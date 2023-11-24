from app import exclusive, record
from graia.ariadne import Ariadne
from graia.ariadne.event.mirai import (
    MemberJoinEvent,
    MemberLeaveEventKick,
    MemberLeaveEventQuit,
    MemberMuteEvent,
    MemberUnmuteEvent
)
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At
from graia.ariadne.model.relationship import Group, Member
from graiax.shortcut.saya import listen

from ..config.admin import AdminConfig


@listen(MemberLeaveEventQuit, MemberLeaveEventKick)
@record("member_leave")
@exclusive
async def member_leave_tell(app: Ariadne, group: Group, member: Member):
    """用户离群提醒"""
    await app.send_group_message(
        group,
        MessageChain(f"可惜了！\n{member.name}({member.id})退群了！"),
    )


@listen(MemberJoinEvent)
@record("member_join")
@exclusive
async def member_join_tell(
        app: Ariadne, group: Group, member: Member, admin: AdminConfig
):
    """用户入群提醒"""
    welcome = admin.member_join_welcome or (
        f"欢迎新人加入{group.name}！进群了就别想跑哦~\n来个star吧球球惹QAQ\n",
        "项目地址：https://github.com/RF-Tar-Railt/RaianBot",
    )

    await app.send_group_message(group, MessageChain(At(member.id), welcome))


@listen(MemberMuteEvent)
@record("member_mute", disable=True)
@exclusive
async def member_mute_tell(app: Ariadne, group: Group, target: Member):
    """用户被禁言提醒"""
    await app.send_group_message(
        group, MessageChain("哎呀，", At(target.id), " 没法说话了！")
    )


@listen(MemberUnmuteEvent)
@record("member_unmute", disable=True)
@exclusive
async def member_unmute_tell(
        app: Ariadne, group: Group, target: Member, operator: Member
):
    """用户被解除禁言提醒, 注意是手动解禁"""
    if operator is not None:
        await app.send_group_message(
            group,
            MessageChain(
                "太好了!\n", At(target.id), " 被", At(operator.id), " 解救了！"
            ),
        )
