from arclet.alconna import Args, command_manager
from arclet.alconna.graia import Alconna, Match
from graia.ariadne.message.element import Image
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.app import Ariadne

from app import command, Sender
from utils.generate_img import create_image


@command(Alconna("帮助", Args["index#选择某条命令的id查看具体帮助", int, -1], help_text="查看帮助"))
async def test2(app: Ariadne, sender: Sender, index: Match[int]):

    cmds = command_manager.get_commands()
    if index.result < 0:
        text = command_manager.all_command_help(show_index=True) + (
            "\n========================================================"
            "\n所有功能均无需 @机器人本身"
            "\n想给点饭钱的话，这里有赞助链接：https://afdian.net/@rf_tar_railt"
            "\n更多功能待开发，如有特殊需求可以向 3165388245 询问"
        )
        return await app.send_message(sender, MessageChain(Image(data_bytes=await create_image(text, cut=120))))
    try:
        text = command_manager.command_help(cmds[index.result].path)
        return await app.send_message(sender, MessageChain(Image(data_bytes=await create_image(text, cut=120))))
    except (IndexError, TypeError):
        return await app.send_message(sender, MessageChain("ID错误！"))
