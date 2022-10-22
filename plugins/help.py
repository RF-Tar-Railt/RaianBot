import random
from app import RaianMain, Sender
from arclet.alconna import ArgField, Args, CommandMeta, command_manager, config
from arclet.alconna.graia import Alconna, AlconnaDispatcher, Match, alcommand, shortcuts
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graiax.text2img.playwright.builtin import md2img


@shortcuts(帮助=MessageChain("渊白帮助"))
@alcommand(
    Alconna(
        "帮助",
        Args[
            "query;OH#选择某条命令的id或者名称查看具体帮助",
            str,
            ArgField(
                -1,
                completion=lambda: f"试试 {random.randint(0, len(command_manager.get_commands()))}",
            ),
        ],
        meta=CommandMeta("查看帮助"),
    )
)
async def send_help(app: Ariadne, sender: Sender, query: Match[str], bot: RaianMain):
    if not query.available:
        md = f"""\
# {bot.config.bot_name} 帮助菜单
#{config.lang.manager_help_header}

| id  | 命令 | 介绍 | 备注 |
| --- | --- | --- | --- |
"""
        cmds = list(filter(lambda x: not x.meta.hide, command_manager.get_commands()))
        command_string = "\n".join(
            (
                f"| {index} | {slot.name.replace('|', '&#124;').replace('[', '&#91;')} | "
                f"{slot.meta.description} | {slot.meta.usage.splitlines()[0] if slot.meta.usage else None} |"
            )
            for index, slot in enumerate(cmds)
        )
        md += command_string

        md += (
            "\n\n---"
            "\n\n* 输入'命令名 --help' 查看特定命令的语法"
            "\n\n* 所有功能均无需 @机器人本身"
            "\n\n* 想给点饭钱的话，这里有赞助链接：https://afdian.net/@rf_tar_railt"
            "\n\n* 更多功能待开发，如有特殊需求可以向 3165388245 询问, 或前往 122680593 交流"
        )
        return await app.send_message(
            sender, MessageChain(Image(data_bytes=await md2img(md)))
        )
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
        return await app.send_message(
            sender, await AlconnaDispatcher.default_send_handler(text)
        )
    except (IndexError, TypeError):
        return await app.send_message(sender, MessageChain("查询失败！"))
