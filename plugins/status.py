import os
import platform
import time
from typing import Union

import psutil
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.saya import AlconnaSchema
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.model import Group, Friend
from graia.saya import Channel
from graia.saya.builtins.broadcast import ListenerSchema

from config import bot_config
from utils.simple_permission import require_admin
from utils.generate_img import create_image

channel = Channel.current()

python_version = platform.python_version()
if platform.uname().system == 'Windows':
    system_version = platform.platform()
else:
    system_version = f'{platform.platform()} {platform.version()}'
total_memory = '%.1f' % (psutil.virtual_memory().total / 1073741824)
pid = os.getpid()

status = Alconna(
    "(状态|设备信息)",
    headers=bot_config.command_prefix,
    help_text="显示机器人运行设备的状态信息",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=status, help_flag="reply")))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot_config.master_id)])
)
async def main(app: Ariadne, sender: Union[Group, Friend]):
    p = psutil.Process(pid)
    started_time = time.localtime(p.create_time())
    running_time = time.time() - p.create_time()
    day = int(running_time / 86400)
    hour = int(running_time % 86400 / 3600)
    minute = int(running_time % 86400 % 3600 / 60)
    second = int(running_time % 86400 % 3600 % 60)
    running_time = f'{f"{day}d " if day else ""}{f"{hour}h " if hour else ""}{f"{minute}m " if minute else ""}{second}s'

    msg_send = (
        f'PID: {pid}\n'
        f'启动时间：{time.strftime("%Y-%m-%d %H:%M:%S", started_time)}\n'
        f'已运行时长：{running_time}\n'
        f'============================\n'
        f'Python 版本：{python_version}\n'
        f'系统版本：{system_version}\n'
        f'CPU 核心数：{psutil.cpu_count()}\n'
        f'CPU 占用率：{psutil.cpu_percent()}%\n'
        f'系统内存占用：{"%.1f" % (psutil.virtual_memory().available / 1073741824)}G / {total_memory}G\n'
    )

    img_bytes = await create_image(msg_send.rstrip())
    await app.sendMessage(sender, MessageChain.create(Image(data_bytes=img_bytes)))
