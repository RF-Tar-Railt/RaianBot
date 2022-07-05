from typing import Union
from arclet.alconna import Args
from arclet.alconna.graia import Alconna, Match
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image
from graia.ariadne.event.mirai import NudgeEvent
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne
from graia.ariadne.util.saya import listen

from app import RaianMain, record, command
from modules.petpet import PetGenerator

rua = Alconna(
    "摸", Args["target", [At, int]],
    headers=[''],
    help_text=f"rua别人 Example: 摸@123456;",
)

pet = PetGenerator("assets/image/rua")


@command(rua, False)
async def draw(
        app: Ariadne,
        member: Member,
        sender: Group,
        target: Match[Union[At, int]]
):
    tg = target.result
    if isinstance(tg, At):
        tg = tg.target
    async with app.service.client_session.get(
            f"https://q1.qlogo.cn/g?b=qq&nk={tg}&s=640"
    ) as resp:
        data = await resp.read()
    image = pet.generate(data)
    await app.send_nudge(member, sender)
    return await app.send_group_message(sender, MessageChain(Image(data_bytes=image.getvalue())))


@record("rua")
@listen(NudgeEvent)
async def draw(
        app: Ariadne,
        event: NudgeEvent,
        bot: RaianMain
):
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
