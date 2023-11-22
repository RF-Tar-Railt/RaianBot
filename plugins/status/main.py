import os
import platform
import time
from secrets import token_hex

import psutil
from arclet.alconna import Alconna
from arclet.alconna.graia import alcommand
from avilla.core import ActionFailed, Context, Picture, RawResource

from app.core import RaianBotService
from app.image import text2img
from app.shortcut import accessable, picture

python_version = platform.python_version()
if platform.uname().system == "Windows":
    system_version = platform.platform()
else:
    system_version = f"{platform.platform()} {platform.version()}"
total_memory = "%.1f" % (psutil.virtual_memory().total / 1073741824)
pid = os.getpid()

cmd = Alconna("status")


@alcommand(cmd, post=True, send_error=True)
@accessable
async def status(ctx: Context, bot: RaianBotService):
    p = psutil.Process(pid)
    started_time = time.localtime(p.create_time())
    running_time = time.time() - p.create_time()
    day = int(running_time / 86400)
    hour = int(running_time % 86400 / 3600)
    minute = int(running_time % 86400 % 3600 / 60)
    second = int(running_time % 86400 % 3600 % 60)
    running_time = f'{f"{day}d " if day else ""}{f"{hour}h " if hour else ""}{f"{minute}m " if minute else ""}{second}s'

    text = (
        f"PID: {pid}\n"
        f'启动时间：{time.strftime("%Y-%m-%d %H:%M:%S", started_time)}\n'
        f"已运行时长：{running_time}\n"
        f"============================\n"
        f"Python 版本：{python_version}\n"
        f"系统版本：{system_version}\n"
        f"CPU 核心数：{psutil.cpu_count()}\n"
        f"CPU 占用率：{psutil.cpu_percent()}%\n"
        f'系统内存占用：{"%.1f" % (psutil.virtual_memory().available / 1073741824)}G / {total_memory}G\n'
    )
    data = await text2img(text)
    try:
        return await ctx.scene.send_message(Picture(RawResource(data)))
    except Exception:
        url = await bot.upload_to_cos(data, f"rand_op_{token_hex(16)}.png")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            return await ctx.scene.send_message(text)
