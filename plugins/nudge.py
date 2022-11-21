from arclet.alconna import Args, ArgField, CommandMeta
from arclet.alconna.graia import Alconna, Match, alcommand, AtID
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.event.mirai import NudgeEvent
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne
from graia.ariadne.util.saya import listen

from app import RaianBotInterface, record
from library.petpet import PetGenerator

rua = Alconna(
    [''],
    "摸",
    Args["target", AtID, ArgField(completion=lambda: "可以不输入东西的")],
    meta=CommandMeta("rua别人", usage="注意: 该命令不需要 “渊白” 开头", example="摸@123456")
)

pet = PetGenerator("assets/image/rua")


@alcommand(rua, private=False)
async def draw(
        app: Ariadne,
        member: Member,
        sender: Group,
        target: Match[int]
):
    async with app.service.client_session.get(f"https://q1.qlogo.cn/g?b=qq&nk={target.result}&s=640") as resp:
        data = await resp.read()
    image = pet.generate(data)
    await app.send_nudge(member, sender)
    return await app.send_group_message(sender, MessageChain(Image(data_bytes=image.getvalue())))


@listen(NudgeEvent)
@record("rua")
async def draw(app: Ariadne, event: NudgeEvent, bot: RaianBotInterface):
    if event.supplicant == bot.config.mirai.account or event.target != bot.config.mirai.account:
        return
    async with app.service.client_session.get(
            f"https://q1.qlogo.cn/g?b=qq&nk={event.supplicant}&s=640"
    ) as resp:
        data = await resp.read()
    image = pet.generate(data)
    if event.group_id:
        return await app.send_group_message(event.group_id, MessageChain(Image(data_bytes=image.getvalue())))
    elif event.friend_id:
        return await app.send_friend_message(event.friend_id, MessageChain(Image(data_bytes=image.getvalue())))
