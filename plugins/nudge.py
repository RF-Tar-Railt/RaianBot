from arclet.alconna import Args
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Image
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.event.mirai import NudgeEvent
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne
from pathlib import Path

from app import RaianMain
from modules.petpet import PetGenerator
from utils.control import require_function

channel = Channel.current()
bot = RaianMain.current()
rua = Alconna(
    "摸", Args["target", [At, int]],
    help_text=f"rua别人 Example: 摸@123456;",
)

pet = PetGenerator("assets/image/rua")


@bot.data.record("rua")
@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=rua, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage], decorators=[require_function("rua")]))
async def draw(
        app: Ariadne,
        member: Member,
        sender: Group,
        result: AlconnaProperty
):
    tg = result.result.main_args['target']
    if isinstance(tg, At):
        tg = tg.target
    async with app.service.client_session.get(
            f"https://q1.qlogo.cn/g?b=qq&nk={tg}&s=640"
    ) as resp:
        data = await resp.read()
    image = pet.generate(data)
    path = Path(f"{bot.config.cache_dir}/plugins/petpet.gif")
    with path.open("wb+") as f:
        f.write(image.getvalue())
    await app.send_nudge(member, sender)
    return await app.send_group_message(sender, MessageChain(Image(path=f"{bot.config.cache_dir}/plugins/petpet.gif")))


@bot.data.record("rua")
@channel.use(ListenerSchema([NudgeEvent], decorators=[require_function("rua")]))
async def draw(
        app: Ariadne,
        event: NudgeEvent
):
    if event.supplicant == bot.config.account or event.target != bot.config.account:
        return
    async with app.service.client_session.get(
            f"https://q1.qlogo.cn/g?b=qq&nk={event.supplicant}&s=640"
    ) as resp:
        data = await resp.read()
    image = pet.generate(data)
    path = Path(f"{bot.config.cache_dir}/plugins/petpet.gif")
    with path.open("wb+") as f:
        f.write(image.getvalue())
    if event.group_id:
        return await app.send_group_message(event.group_id, MessageChain(Image(path=f"{bot.config.cache_dir}/plugins/petpet.gif")))
    elif event.friend_id:
        return await app.send_friend_message(event.friend_id, MessageChain(Image(path=f"{bot.config.cache_dir}/plugins/petpet.gif")))
