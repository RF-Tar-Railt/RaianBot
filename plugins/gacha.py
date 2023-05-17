from typing import NamedTuple
from app import RaianBotService, Sender, Target, record, meta_export, exclusive, accessable, RaianBotInterface
from arclet.alconna import Alconna, Field, Args, CommandMeta
from arclet.alconna.graia import Match, alcommand
from arknights_toolkit.gacha import ArknightsGacha, GachaUser
from fastapi.responses import JSONResponse, Response
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.util.cooldown import CoolDown
from graiax.fastapi import route
from plugins.config.gacha import GachaConfig

bot = RaianBotService.current()
config = bot.config.plugin.get(GachaConfig)
gacha = ArknightsGacha(f"{bot.config.plugin_cache_dir / 'gachapool.json'}")
cd = CoolDown(config.cooldown)

class arkgacha_proba(NamedTuple):
    six_statis: int
    six_per: int


meta_export(user_meta=[arkgacha_proba])


@route.route(["GET"], "/gacha")
async def get_gacha(count: int = 10, per: int = 2, status: int = 0, img: bool = False):
    guser = GachaUser(per, status)
    if img:
        return Response(gacha.gacha_with_img(guser, count), media_type="image/png")
    data = gacha.gacha(guser, count)
    return JSONResponse(
        [[i._asdict() for i in line] for line in data], headers={"charset": "utf-8"}
    )


@route.route(["GET"], "/gacha/sim")
async def get_sim_gacha(per: int = 2, status: int = 0):
    from arknights_toolkit.gacha.simulate import simulate_image

    guser = GachaUser(per, status)
    data = gacha.gacha(guser, 10)
    return Response(await simulate_image(data[0]), media_type="image/png")


@alcommand(
    Alconna(
        "(抽卡|寻访)",
        Args["count", int, Field(10, completion=lambda: "试试输入 300")],
        meta=CommandMeta("模拟方舟寻访", example="$抽卡 300"),
    ),
    send_error=True,
)
@record("抽卡")
@exclusive
@accessable
async def gacha_(app: Ariadne, sender: Sender, target: Target, count: Match[int], interface: RaianBotInterface):
    """模拟抽卡"""
    count_ = min(max(count.result, 1), 300)
    if interface.data.exist(target.id):
        user = interface.data.get_user(target.id)
        proba = user.get(arkgacha_proba, arkgacha_proba(0, 2))
        guser = GachaUser(proba.six_per, proba.six_statis)
        data = gacha.gacha_with_img(guser, count_)
        user.set(arkgacha_proba(guser.six_statis, guser.six_per))
        interface.data.update_user(user)
    else:
        guser = GachaUser()
        data = gacha.gacha_with_img(guser, count_)
        await app.send_message(sender, "您未签到，抽卡水位是继承不了的说")
    return await app.send_message(sender, MessageChain(Image(data_bytes=data)))


@alcommand(Alconna("十连", meta=CommandMeta("生成仿真寻访图", usage="灰色头像表示新干员但是头图未更新")))
@record("抽卡")
@exclusive
@accessable
async def simulate(app: Ariadne, sender: Sender, target: Target, interface: RaianBotInterface):
    from arknights_toolkit.gacha.simulate import simulate_image
    async with cd.trigger(target.id, int) as res:
        if not res[1]:
            return
    if interface.data.exist(target.id):
        user = interface.data.get_user(target.id)
        proba = user.get(arkgacha_proba, arkgacha_proba(0, 2))
        guser = GachaUser(proba.six_per, proba.six_statis)
        ops = gacha.gacha(guser, 10)
        data = await simulate_image(ops[0])
        user.set(arkgacha_proba(guser.six_statis, guser.six_per))
        interface.data.update_user(user)
    else:
        guser = GachaUser()
        ops = gacha.gacha(guser, 10)
        data = await simulate_image(ops[0])
        await app.send_message(sender, "您未签到，抽卡水位是继承不了的说")
    return await app.send_message(sender, MessageChain(Image(data_bytes=data)))


@alcommand(Alconna("卡池更新", meta=CommandMeta("更换卡池")))
@record("抽卡")
@exclusive
@accessable
async def change(app: Ariadne, sender: Sender):
    if new := (await gacha.update()):
        return await app.send_message(
            sender, MessageChain(f"卡池已更新至: {new.title}", Image(url=new.pool))
        )
    return await app.send_message(sender, "卡池已经是最新状态！")
