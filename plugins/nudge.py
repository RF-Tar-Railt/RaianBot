from arclet.alconna import Args, Field, CommandMeta
from arclet.alconna.graia import Alconna, Match, alcommand
from arclet.alconna.ariadne import AtID
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.event.mirai import NudgeEvent
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne
from graia.ariadne.util.cooldown import CoolDown
from graiax.shortcut.saya import listen

from app import RaianBotInterface, record, accessable, exclusive
from library.petpet import PetGenerator

rua = Alconna(
    [''],
    "摸",
    Args["target", AtID, Field(completion=lambda: "可以不输入东西的")],
    meta=CommandMeta("rua别人", usage="注意: 该命令不需要 “渊白” 开头", example="摸@123456")
)

pet = PetGenerator("assets/image/rua")
cd = CoolDown(1)


@alcommand(rua, private=False)
@record("rua")
@exclusive
@accessable
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
@accessable
async def draw(app: Ariadne, event: NudgeEvent, bot: RaianBotInterface):
    if event.supplicant in bot.base_config.bots or event.target != bot.config.account:
        return
    async with cd.trigger(event.group_id or event.friend_id, int) as res:
        if not res[1]:
            if event.group_id:
                return await app.send_group_message(event.group_id, "戳太快了！")
            else:
                return await app.send_friend_message(event.friend_id, "戳太快了！")
    async with app.service.client_session.get(
            f"https://q1.qlogo.cn/g?b=qq&nk={event.supplicant}&s=640"
    ) as resp:
        data = await resp.read()
    image = pet.generate(data)
    if event.group_id:
        return await app.send_group_message(event.group_id, MessageChain(Image(data_bytes=image.getvalue())))
    elif event.friend_id:
        return await app.send_friend_message(event.friend_id, MessageChain(Image(data_bytes=image.getvalue())))
