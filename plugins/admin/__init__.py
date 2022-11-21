import asyncio

from app import RaianBotService
from graiax.shortcut.saya import every
from . import event, exception, mute, group, control
from ..config.admin import AdminConfig

bot = RaianBotService.current()
admin: AdminConfig = bot.config.plugin.get(AdminConfig)

if admin.enable_announcement:
    from . import announcement

if admin.enable_fetch_flash:
    from . import flash

if admin.enable_start_report:
    from . import start

if admin.enable_member_report:
    from . import member

if admin.enable_request_handle:
    from . import request


@every(1, "hour")
async def save():
    bot.data.save()
    await asyncio.sleep(0.1)
