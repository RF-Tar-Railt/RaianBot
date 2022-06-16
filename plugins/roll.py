from typing import Union
from arclet.alconna import Args, Empty
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.ariadne.message.element import Image
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend, Member
from graia.ariadne.app import Ariadne


from app import RaianMain

channel = Channel.current()
bot = RaianMain.current()
draw = Alconna(
    r"r{pattern:[0-z|#\+]+}", Args["expect;O", int]["event", str, Empty],
    headers=bot.config.command_prefix,
    help_text=f"模拟coc掷骰功能",
)