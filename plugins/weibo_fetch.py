from typing import Union
from arclet.alconna import Args
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Forward, ForwardNode, Source, Image
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from config import bot_config
from modules.weibo import WeiboAPI

channel = Channel.current()

weibo_fetch = Alconna(
    "{target}动态", Args["index":int:0],
    headers=bot_config.command_prefix,
    help_text="从微博获取指定用户的动态 Usage: index 表示从最前动态排起的第几个动态; Example: .育碧动态;",
)
api = WeiboAPI("data/plugins/weibo_data.json")


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=weibo_fetch, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def fetch(app: Ariadne, sender: Union[Group, Friend], source: Source, result: AlconnaProperty):
    target = result.source.sender
    arp = result.result
    if dynamic := await api.get_dynamic(arp.header['target'], arp.index):
        url = MessageChain.create(dynamic[2])
        text = MessageChain.create(dynamic[0], *(Image(url=i) for i in dynamic[1]))
        return await app.sendMessage(sender, MessageChain.create(
            Forward(
                ForwardNode(target=target, time=source.time, message=text),
                ForwardNode(target=target, time=source.time, message=url)
            )
        ))
