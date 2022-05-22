from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne

from config import bot_config
from data import bot_data

channel = Channel.current()

sign = Alconna(
    "签到",
    headers=bot_config.command_prefix,
    help_text="在机器人处登记用户信息",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=sign, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage]))
async def sign_up(app: Ariadne, sender: Group, member: Member, source: Source):
    group_data = bot_data.get_group(sender.id)
    if group_data:
        if "sign" in group_data.disabled:
            return
        elif group_data.in_blacklist:
            return
    if bot_data.exist(member.id):
        return await app.sendGroupMessage(
            sender, MessageChain.create("您已与我签到!\n一人签到一次即可\n之后您不再需要找我签到"),
            quote=source.id
        )
    bot_data.add_user(member.id)
    return await app.sendGroupMessage(
        sender, MessageChain.create("签到成功！\n现在您可以抽卡与抽签了\n之后您不再需要找我签到"),
        quote=source.id
    )
