from secrets import token_hex
from typing import Union

from arclet.alconna import Alconna, Args, CommandMeta, Field
from arclet.alconna.graia import Match, alcommand
from arknights_toolkit.random_operator import RandomOperator
from avilla.core import ActionFailed, Context, MessageChain, Nick, Notice, Picture, RawResource
from avilla.standard.core.message import MessageReceived

from app.core import RaianBotService
from app.image import text2img
from app.interrupt import FunctionWaiter
from app.shortcut import accessable, is_qqapi_group, picture, record


@alcommand(
    Alconna(
        "测试干员",
        Args["name?#你的代号", [str, Notice], Field(completion=lambda: "你的代号是?")],
        meta=CommandMeta("依据名字测试你会是什么干员", example="$测试干员 海猫"),
    ),
    send_error=True,
    post=True,
)
@record("随机干员")
# @exclusive
@accessable
async def ro(ctx: Context, name: Match[Union[str, Notice]], bot: RaianBotService):
    """依据名字随机生成干员"""
    if name.available:
        _name = name.result
        if isinstance(_name, str):
            text = RandomOperator().generate(_name)
        else:
            text = RandomOperator().generate(_name.display or (await ctx.client.pull(Nick)).nickname)
    else:
        if is_qqapi_group(ctx):
            await ctx.scene.send_message("请输入测试干员的名称：")

            async def waiter(waiter_ctx: Context, message: MessageChain):
                ans = str(message.exclude(Notice)).lstrip()
                if waiter_ctx.scene.pattern == ctx.scene.pattern:
                    return ans

            _name = await FunctionWaiter(
                waiter,
                [MessageReceived],
                block_propagation=ctx.client.follows("::friend") or ctx.client.follows("::guild.user"),
            ).wait(timeout=30, default=None)
            if _name is None:
                return await ctx.scene.send_message("等待已超时，取消生成干员信息。")
            text = RandomOperator().generate(_name)
        else:
            text = RandomOperator().generate((await ctx.client.pull(Nick)).nickname)
    data = await text2img(text)
    try:
        return await ctx.scene.send_message(Picture(RawResource(data)))
    except Exception:
        url = await bot.upload_to_cos(data, f"rand_op_{token_hex(16)}.png")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            return await ctx.scene.send_message(text)
