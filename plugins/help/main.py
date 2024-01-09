import random
from secrets import token_hex

from arclet.alconna import Alconna, Args, CommandMeta, Field, command_manager
from arclet.alconna.graia import Match, alcommand, AlconnaGraiaService
from arclet.alconna.avilla import AlconnaAvillaAdapter
from avilla.core import ActionFailed, Context, MessageChain, Notice, Picture, RawResource, Text
from avilla.core.tools.filter import Filter
from avilla.elizabeth.account import ElizabethAccount
from avilla.qqapi.account import QQAPIAccount
from avilla.standard.core.message import MessageReceived
from graia.saya.builtins.broadcast.shortcut import dispatch, listen
from tarina import lang

from app.config import BotConfig
from app.core import RaianBotService
from app.image import md2img
from app.shortcut import accessable, allow, exclusive, picture

cmd_help = Alconna(
    "帮助",
    Args[
        "query#选择某条命令的id或者名称查看具体帮助;/?",
        str,
        Field(
            -1,
            completion=lambda: f"试试 {random.randint(0, len(command_manager.get_commands()))}",
            unmatch_tips=lambda x: f"预期输入为某个命令的id或者名称，而不是 {x}\n例如：/帮助 0",
        ),
    ],
    meta=CommandMeta("查看帮助", extra={"supports": {"mirai", "qqapi"}}),
)
cmd_help.shortcut(r"帮助(\d+)", {"prefix": True, "args": ["{0}"]})
cmd_help.shortcut("菜单", {"prefix": True})


@listen(MessageReceived)
@dispatch(Filter.cx.scene.follows("::group"))
@allow(QQAPIAccount)
async def send_(ctx: Context, bot: RaianBotService, config: BotConfig, message: MessageChain, alc: AlconnaGraiaService):
    if str(message.exclude(Notice)).lstrip() != "":
        return
    alc: AlconnaGraiaService[AlconnaAvillaAdapter]
    if not alc.get_adapter().is_tome(message, ctx.account.route):
        return
    plat: str = {ElizabethAccount: "mirai", QQAPIAccount: "qqapi"}.get(ctx.account.__class__, "mirai")  # type: ignore
    md = f"""\
# {config.name} {config.account} 帮助菜单
#{lang.require('manager', 'help_header')}

| id  | 命令 | 介绍 | 备注 |
| --- | --- | --- | --- |
"""
    cmds = list(filter(lambda x: not x.meta.hide, command_manager.get_commands()))
    command_string = "\n".join(
        (
            f"| {index} | {bot.config.command.headers[0]}{slot.name.replace('|', '&#124;').replace('[', '&#91;')} | "
            f"{slot.meta.description} | {slot.meta.usage.splitlines()[0] if slot.meta.usage else None} |"
        )
        for index, slot in enumerate(cmds)
        if plat in slot.meta.extra["supports"]
    )
    md += command_string

    md += (
        "\n\n---"
        f"\n\n* 输入'命令名 {bot.config.command.help[0]}' 查看特定命令的语法"
        "\n\n* 部分情况下需要先 @机器人本身 才能使用指令（例如当本 bot携带 机器人 标识时）"
        "\n\n* 想给点饭钱的话，这里有赞助链接：https://afdian.net/@rf_tar_railt"
        "\n\n* 更多功能待开发，如有特殊需求可以向 3165388245 询问, 或前往 122680593 交流"
    )
    img = await md2img(md)
    try:
        return await ctx.scene.send_message(Picture(RawResource(img)))
    except Exception:
        url = await bot.upload_to_cos(img, f"help_{token_hex(16)}.jpg")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            return await ctx.scene.send_message(command_manager.all_command_help())


@alcommand(
    Alconna("help", meta=CommandMeta("查看帮助", extra={"supports": {"mirai", "qqapi"}})),
    post=True,
    send_error=True,
)
@exclusive
@accessable
async def send_text_help(ctx: Context):
    return await ctx.scene.send_message(command_manager.all_command_help())


@alcommand(cmd_help, post=True, send_error=True)
@exclusive
@accessable
async def send_help(ctx: Context, query: Match[str], bot: RaianBotService, config: BotConfig, alc: AlconnaGraiaService):
    if not query.available:
        return await send_(ctx, bot, config, MessageChain([Notice(ctx.self)]), alc)
    try:
        if query.result.isdigit():
            cmds = list(command_manager.all_command_raw_help().keys())
            text = command_manager.get_command(cmds[int(query.result)]).get_help()
        else:
            cmds = list(
                filter(
                    lambda x: query.result in x,
                    command_manager.all_command_raw_help().keys(),
                )
            )
            text = command_manager.get_command(cmds[0]).get_help()
        img = await md2img(text)
        try:
            return await ctx.scene.send_message(Picture(RawResource(img)))
        except Exception:
            url = await bot.upload_to_cos(img, f"help_{token_hex(16)}.jpg")
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed:
                output = (
                    text.replace("&lt;", "<")
                    .replace("&gt;", ">")
                    .replace("\n\n", "\n")
                    .replace("##", "#")
                    .replace("**", "")
                )
                return await ctx.scene.send_message(output)
    except (IndexError, TypeError):
        return await ctx.scene.send_message("查询失败！")
