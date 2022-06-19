from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne


from app import RaianMain
from utils.control import require_function

bot = RaianMain.current()
channel = Channel.current()

sign = Alconna(
    "签到",
    headers=bot.config.command_prefix,
    help_text="在机器人处登记用户信息",
)


@bot.data.record('sign')
@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=sign, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage], decorators=[require_function('sign')]))
async def sign_up(app: Ariadne, sender: Group, member: Member, source: Source):
    """在机器人处登记信息"""
    if bot.data.exist(member.id):
        return await app.send_group_message(
            sender, MessageChain("您已与我签到!\n一人签到一次即可\n之后您不再需要找我签到"),
            quote=source.id
        )
    bot.data.add_user(member.id)
    return await app.send_group_message(
        sender, MessageChain("签到成功！\n现在您可以抽卡与抽签了\n之后您不再需要找我签到"),
        quote=source.id
    )
