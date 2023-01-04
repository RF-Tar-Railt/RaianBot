from app import BotConfig, exclusive
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage, TempMessage, MessageEvent
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import FlashImage
from graiax.shortcut.saya import listen, priority


@listen(GroupMessage, FriendMessage, TempMessage)
@priority(10)
@exclusive
async def _flash(app: Ariadne, message: MessageChain, config: BotConfig, event: MessageEvent):
    if not message.has(FlashImage):
        return
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(f"闪照来源：{event}")
    )
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(message.get_first(FlashImage).to_image()),
    )
