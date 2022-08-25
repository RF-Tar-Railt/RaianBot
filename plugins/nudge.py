from arclet.alconna import Args, ArgField, CommandMeta
from arclet.alconna.graia import Alconna, Match, command, AtID
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.event.mirai import NudgeEvent
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne
from graia.ariadne.util.saya import listen

from app import RaianMain, record
from modules.petpet import PetGenerator

rua = Alconna(
    "摸", Args["target", AtID, ArgField(completion=lambda: "可以不输入东西的")],
    headers=[''], meta=CommandMeta("rua别人  注意: 该命令不需要 “渊白” 开头", example="摸@123456")
)

pet = PetGenerator("assets/image/rua")


@command(rua, private=False)
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


@record("rua")
@listen(NudgeEvent)
async def draw(app: Ariadne, event: NudgeEvent, bot: RaianMain):
    if event.supplicant == bot.config.account or event.target != bot.config.account:
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
