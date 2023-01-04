import asyncio

from app import RaianBotService, DataInstance
from graiax.shortcut.saya import every
from loguru import logger
from . import event, exception, mute, group, control, announcement, start
from ..config.admin import AdminConfig

bot = RaianBotService.current()
admin: AdminConfig = bot.config.plugin.get(AdminConfig)

if admin.enable_fetch_flash:
    from . import flash

if admin.enable_member_report:
    from . import member

if admin.enable_request_handle:
    from . import request


@every(1, "hour")
async def save():
    datas = DataInstance.get()
    for account, data in datas.items():
        data.save()
        logger.debug(f"账号 {account} 数据保存完毕")
        await asyncio.sleep(0.1)
