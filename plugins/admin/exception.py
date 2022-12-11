from app import RaianBotInterface
from app.image import render_markdown
from app.report import reports_md
from graia.ariadne import Ariadne
from graia.ariadne.exception import AccountMuted
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.broadcast.builtin.event import ExceptionThrown, ExceptionThrowed
from graiax.shortcut.saya import listen, priority

from .event import AccountMuted as AccountMutedEvent


@listen(ExceptionThrown)
@priority(13)
async def report(app: Ariadne, event: ExceptionThrown, interface: RaianBotInterface):
    config = interface.config
    if isinstance(event.exception, AccountMuted) and isinstance(event.event, GroupMessage):
        for listener in app.broadcast.default_listener_generator(AccountMutedEvent):
            await listener.callable(app, event.event.sender.group, interface)
        return
    tb = reports_md(event.exception)
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(Image(data_bytes=await render_markdown(tb))),
    )


@listen(ExceptionThrowed)
@priority(13)
async def report(app: Ariadne, event: ExceptionThrowed, interface: RaianBotInterface):
    config = interface.config
    if isinstance(event.exception, AccountMuted) and isinstance(event.event, GroupMessage):
        for listener in app.broadcast.default_listener_generator(AccountMutedEvent):
            await listener.callable(app, event.event.sender.group, interface)
        return
    tb = reports_md(event.exception)
    tb = f"## 概览\n\n在处理 {event.event} 时出现如下问题:\n{tb}"
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(Image(data_bytes=await render_markdown(tb))),
    )
