from app import BotConfig
from graia.ariadne import Ariadne
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import FlashImage
from graiax.shortcut.saya import listen


@listen(GroupMessage, FriendMessage)
async def _flash(app: Ariadne, message: MessageChain, config: BotConfig):
    if not message.has(FlashImage):
        return
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(message.get_first(FlashImage).to_image()),
    )
