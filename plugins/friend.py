from arclet.alconna import Args, Arpamar, AllParam, CommandMeta
from arclet.alconna.graia import Alconna, Match, alcommand
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import FriendMessage
from graia.ariadne.model.relationship import Friend
from graia.ariadne.util.saya import listen, decorate
from graia.ariadne.app import Ariadne

from app import require_admin, RaianMain


@listen(FriendMessage)
async def forward(app: Ariadne, friend: Friend, message: MessageChain, bot: RaianMain):
    if friend.id == bot.config.master_id:
        return
    await app.send_friend_message(bot.config.master_id, MessageChain(f"来自 {friend.nickname}({friend.id}):"))
    return await app.send_friend_message(bot.config.master_id, message.as_sendable())


@alcommand(Alconna([""], "回复", Args["target", int]["content", AllParam], meta=CommandMeta(hide=True)))
@decorate(require_admin(True))
async def reply(app: Ariadne, master: Friend, target: Match[int], result: Arpamar):
    message = result.origin.as_sendable().replace(f"回复 {target.result}\n", "")  # type: ignore
    try:
        await app.send_friend_message(target.result, message)
    except Exception as e:
        await app.send_friend_message(master, MessageChain(str(e)))