import asyncio
from pathlib import Path
from loguru import logger

from graia.broadcast import Broadcast
from graia.ariadne.app import Ariadne
from graia.ariadne.adapter import MiraiSession
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Group
from graia.saya import Saya
from graia.saya.builtins.broadcast import BroadcastBehaviour
from arclet.alconna.graia.saya import AlconnaBehaviour
from arclet.alconna import command_manager

from config import bot_config
from data import bot_data

loop = asyncio.get_event_loop()
bcc = Broadcast(loop=loop)
bot = Ariadne(
    loop=loop,
    broadcast=bcc,
    use_loguru_traceback=False,
    connect_info=MiraiSession(
        host=bot_config.url,
        verify_key=bot_config.verify_key,
        account=bot_config.account,
    )
)
saya = Saya(bcc)
saya.install_behaviours(
    BroadcastBehaviour(broadcast=bcc),
    AlconnaBehaviour(broadcast=bcc, manager=command_manager)
)

plugin_path = Path(bot_config.plugin_path)
if not plugin_path.is_dir():
    logger.error("插件路径应该为一存在的文件夹")
else:
    with saya.module_context():
        for file in plugin_path.iterdir():
            if file.is_file():
                name = file.name.split('.')[0]
                if name in bot_config.disabled_plugins:
                    continue
            else:
                name = file.name
            if name.startswith("_"):
                continue
            saya.require(f"{plugin_path.name}.{name}")


@bcc.receiver(GroupMessage, priority=7)
async def init_group(app: Ariadne, group: Group):
    if not bot_data.exist(group.id):
        bot_data.add_group(group.id)
        bot_data.cache['all_joined_group'].append(group.id)
        return await app.sendFriendMessage(
            bot_config.master_id, MessageChain.create(f"{group.name} 初始化完成")
        )


bot.launch_blocking()
logger.debug(bot_data.cache)
bot_data.save()
