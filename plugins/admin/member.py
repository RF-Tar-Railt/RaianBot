from avilla.core import Context, Notice
from avilla.core.event import MemberCreated, MemberDestroyed, MetadataModified
from avilla.core.tools.filter import Filter
from avilla.elizabeth.account import ElizabethAccount
from avilla.standard.core.privilege import MuteInfo
from graia.amnesia.message import MessageChain
from graia.saya.builtins.broadcast.shortcut import dispatch, listen

from app.shortcut import allow, exclusive, record


@listen(MemberDestroyed)
@record("member_leave")
@exclusive
@allow(ElizabethAccount)
async def member_leave_tell(ctx: Context):
    """用户离群提醒"""
    await ctx.scene.send_message(f"可惜了！\n{(await ctx.endpoint.nick()).name}({ctx.endpoint.user})退群了！")


@listen(MemberCreated)
@record("member_join")
@exclusive
@allow(ElizabethAccount)
async def member_join_tell(
    ctx: Context,
):
    """用户入群提醒"""
    welcome = f"欢迎新人加入{(await ctx.scene.nick()).name}！进群了就别想跑哦~"
    await ctx.scene.send_message(MessageChain([Notice(ctx.client), welcome]))


@listen(MetadataModified)
@record("member_mute", disable=True)
@dispatch(
    Filter()
    .dispatch(MetadataModified)
    .assert_true(lambda e: e.route is MuteInfo)
    .assert_true(lambda e: e.details[MuteInfo.inh(lambda x: x.muted)].current)
)
@exclusive
@allow(ElizabethAccount)
async def member_mute_tell(ctx: Context, event: MetadataModified):
    """用户被禁言提醒"""
    await ctx.scene.send_message(MessageChain(["哎呀，", Notice(event.endpoint), " 没法说话了！"]))


@listen(MetadataModified)
@record("member_unmute", disable=True)
@dispatch(
    Filter()
    .dispatch(MetadataModified)
    .assert_true(lambda e: e.route is MuteInfo)
    .assert_false(lambda e: e.details[MuteInfo.inh(lambda x: x.muted)].current)
)
@exclusive
@allow(ElizabethAccount)
async def member_unmute_tell(ctx: Context, event: MetadataModified):
    """用户被解除禁言提醒, 注意是手动解禁"""
    if event.operator is None:
        return
    await ctx.scene.send_message(
        MessageChain(
            [
                "太好了!\n",
                Notice(event.endpoint),
                " 被",
                Notice(event.operator),
                " 解救了！",
            ]
        )
    )
