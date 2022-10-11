from app import RaianMain, Sender, Target, record
from arclet.alconna import Args, CommandMeta, ArgField
from arclet.alconna.graia import Alconna, Match, alcommand
from arknights_toolkit.gacha import ArknightsGacha, GachaUser
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.util.saya import dispatch, listen
from graia.ariadne.util.cooldown import CoolDown
from graia.ariadne.event.lifecycle import ApplicationLaunch

bot = RaianMain.current()
gacha = ArknightsGacha(bot.config.plugin.get("gacha", "assets/data/gacha_arknights.json"))


@listen(ApplicationLaunch)
async def gacha_init():
    await gacha.initialize()


@alcommand(
    Alconna(
        "(抽卡|寻访)",
        Args["count", int, ArgField(10, completion=lambda: "试试输入 300")],
        meta=CommandMeta("模拟方舟寻访", example="$抽卡 300"),
        send_error=True,
    )
)
@record("抽卡")
async def gacha_(app: Ariadne, sender: Sender, target: Target, count: Match[int]):
    """模拟抽卡"""
    count = min(max(count.result, 1), 300)
    if bot.data.exist(target.id):
        user = bot.data.get_user(target.id)
        if not user.additional.get("gacha_proba"):
            user.additional["gacha_proba"] = {"arknights": [0, 2]}
        elif not user.additional["gacha_proba"].get("arknights"):
            user.additional["gacha_proba"]["arknights"] = [0, 2]
        six_statis, six_per = user.additional["gacha_proba"]["arknights"]
        guser = GachaUser(six_per, six_statis)
        data = gacha.gacha_with_img(guser, count)
        user.additional["gacha_proba"]["arknights"] = [guser.six_statis, guser.six_per]
        bot.data.update_user(user)
    else:
        guser = GachaUser()
        data = gacha.gacha_with_img(guser, count)
    return await app.send_message(sender, MessageChain(Image(data_bytes=data)))


@record("抽卡")
@dispatch(CoolDown(1.5))
@alcommand(Alconna("十连", meta=CommandMeta("生成仿真寻访图", usage="有1.5s的时间限制")))
async def simulate(app: Ariadne, sender: Sender, target: Target):
    from arknights_toolkit.gacha import simulate_image
    if bot.data.exist(target.id):
        user = bot.data.get_user(target.id)
        if not user.additional.get("gacha_proba"):
            user.additional["gacha_proba"] = {"arknights": [0, 2]}
        elif not user.additional["gacha_proba"].get("arknights"):
            user.additional["gacha_proba"]["arknights"] = [0, 2]
        six_statis, six_per = user.additional["gacha_proba"]["arknights"]
        guser = GachaUser(six_per, six_statis)
        ops = gacha.gacha(guser, 10)
        data = await simulate_image(ops[0])
        user.additional["gacha_proba"]["arknights"] = [guser.six_statis, guser.six_per]
        bot.data.update_user(user)
    else:
        guser = GachaUser()
        ops = gacha.gacha(guser, 10)
        data = await simulate_image(ops[0])
    return await app.send_message(sender, MessageChain(Image(data_bytes=data)))


@record("抽卡")
@alcommand(Alconna("卡池更新", meta=CommandMeta("更换卡池")))
async def change(app: Ariadne, sender: Sender):
    if new := (await gacha.update()):
        return await app.send_message(sender, MessageChain(f"卡池已更新至: {new.title}", Image(url=new.pool)))
    return await app.send_message(sender, "卡池已经是最新状态！")
