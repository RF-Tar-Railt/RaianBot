from arclet.alconna import Alconna, Args, CommandMeta
from arclet.alconna.graia import Match, alcommand
from avilla.core import Context, MessageChain, MessageReceived
from avilla.core.tools.filter import Filter
from avilla.standard.core.request import RequestReceived
from graia.saya.builtins.broadcast.shortcut import dispatch, listen

from app.config import BotConfig
from app.core import RaianBotService
from app.interrupt import FunctionWaiter

cmd = Alconna(
    "自动同意请求",
    Args["opt", {"on": True, "off": False, ...: True}],
    meta=CommandMeta(
        "自动同意请求",
        usage="",
        example="",
        extra={"supports": {"mirai"}},
        hide=True,
    ),
)


@alcommand(cmd, post=True, send_error=True)
async def auto_accept(ctx: Context, opt: Match[bool], bot: RaianBotService):
    if opt.result:
        await ctx.scene.send_message("已开启自动同意请求")
        bot.cache["auto_accept"] = True
    else:
        await ctx.scene.send_message("已关闭自动同意请求")
        bot.cache["auto_accept"] = False


@listen(RequestReceived)
@dispatch(Filter().dispatch(RequestReceived).assert_true(lambda e: e.request.request_type == "elizabeth::new_friend"))
async def get_friend_accept(ctx: Context, event: RequestReceived, bot: RaianBotService, conf: BotConfig):
    """
    收到好友申请
    """
    req = event.request
    await ctx.account.get_context(conf.master()).scene.send_message(
        f"""\
收到添加好友事件
QQ：{req.sender.pattern['contact']}
昵称：{(await ctx.client.nick()).name}
申请消息：{req.message}"
        """
    )
    if bot.cache.get("auto_accept", False):
        await req.accept()
        await ctx.account.get_context(conf.master()).scene.send_message("已自动同意请求")
    else:

        async def waiter(w_ctx: Context, msg: MessageChain):
            if w_ctx.client.follows(conf.master().display):
                return str(msg)

        await ctx.account.get_context(conf.master()).scene.send_message("处理请求等待中")
        res = await FunctionWaiter(waiter, [MessageReceived], block_propagation=True).wait(120)
        if not res:
            await req.reject("管理员超时未回复，请尝试重新发送请求")
            await ctx.account.get_context(conf.master()).scene.send_message("因为超时已拒绝请求")
            return
        if res in ("同意", "yes", "y", "ok", "好", "是", "同意请求"):
            await req.accept()
            await ctx.account.get_context(conf.master()).scene.send_message("已同意请求")
        else:
            await req.reject("拒绝请求")
            await ctx.account.get_context(conf.master()).scene.send_message("已拒绝请求")


@listen(RequestReceived)
@dispatch(
    Filter().dispatch(RequestReceived).assert_true(lambda e: e.request.request_type == "elizabeth::invited_join_group")
)
async def bot_invite(ctx: Context, event: RequestReceived, bot: RaianBotService, conf: BotConfig):
    """
    被邀请入群
    """
    req = event.request
    async for friend in ctx.query("land.friend"):
        if friend.pattern["friend"] == req.sender.pattern["member"]:
            await ctx.account.get_context(conf.master()).scene.send_message(
                f"""\
收到邀请入群事件
邀请者：{req.sender.pattern['member']}
群号：{req.sender.pattern['group']}
群名：{(await ctx.scene.summary()).name}
"""
            )
            if bot.cache.get("auto_accept", False):
                await req.accept()
                await ctx.account.get_context(conf.master()).scene.send_message("已自动同意请求")
                return

            async def waiter(w_ctx: Context, msg: MessageChain):
                if w_ctx.client.follows(conf.master().display):
                    return str(msg)

            await ctx.account.get_context(friend).scene.send_message("请等待机器人管理员处理该请求")
            await ctx.account.get_context(conf.master()).scene.send_message("处理请求等待中")
            res = await FunctionWaiter(waiter, [MessageReceived], block_propagation=True).wait(120)
            if not res:
                await req.reject("管理员超时未回复，请尝试重新发送请求")
                await ctx.account.get_context(friend).scene.send_message("管理员超时未回复，请尝试重新发送请求")
                await ctx.account.get_context(conf.master()).scene.send_message("因为超时已拒绝请求")
                return
            if res in ("同意", "yes", "y", "ok", "好", "是", "同意请求"):
                await req.accept()
                await ctx.account.get_context(conf.master()).scene.send_message("已同意请求")
                await ctx.account.get_context(friend).scene.send_message("已同意请求")
            else:
                await req.reject("拒绝请求")
                await ctx.account.get_context(friend).scene.send_message("已拒绝请求")
                await ctx.account.get_context(conf.master()).scene.send_message("已拒绝请求")
            return
    return await req.reject("请先加机器人好友")
