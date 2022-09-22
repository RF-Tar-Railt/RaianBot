from app import RaianMain, Sender, Target, record
from arclet.alconna import Args, CommandMeta, ArgField
from arclet.alconna.graia import Alconna, Match, alcommand
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.util.saya import dispatch
from graia.ariadne.util.cooldown import CoolDown
from modules.arknights import ArknightsGacha, simulate_ten_generate


@alcommand(
    Alconna(
        "(抽卡|寻访)",
        Args["count", int, ArgField(10, completion=lambda: "试试输入 300")],
        meta=CommandMeta("模拟方舟寻访", example="$抽卡 300"),
        send_error=True,
    )
)
@record("抽卡")
async def gacha_(
        app: Ariadne, sender: Sender, target: Target, count: Match[int], bot: RaianMain
):
    """模拟抽卡"""
    file = bot.config.plugin.get("gacha", "assets/data/gacha_arknights.json")
    count = min(max(count.result, 1), 300)
    if bot.data.exist(target.id):
        user = bot.data.get_user(target.id)
        if not user.additional.get("gacha_proba"):
            user.additional["gacha_proba"] = {"arknights": [0, 2]}
        elif not user.additional["gacha_proba"].get("arknights"):
            user.additional["gacha_proba"]["arknights"] = [0, 2]
        six_statis, six_per = user.additional["gacha_proba"]["arknights"]
        gacha = ArknightsGacha(file=file, six_per=six_per, six_statis=six_statis)
        data = gacha.gacha(count)
        user.additional["gacha_proba"]["arknights"] = [gacha.six_statis, gacha.six_per]
        bot.data.update_user(user)
    else:
        gacha = ArknightsGacha(file=file)
        data = gacha.gacha(count)
    return await app.send_message(sender, MessageChain(Image(data_bytes=data)))


@record("抽卡")
@dispatch(CoolDown(1.5))
@alcommand(Alconna("十连", meta=CommandMeta("生成仿真寻访图", usage="有1.5s的时间限制")))
async def simulate(app: Ariadne, sender: Sender, target: Target, bot: RaianMain):
    file = bot.config.plugin.get("gacha", "assets/data/gacha_arknights.json")
    if bot.data.exist(target.id):
        user = bot.data.get_user(target.id)
        if not user.additional.get("gacha_proba"):
            user.additional["gacha_proba"] = {"arknights": [0, 2]}
        elif not user.additional["gacha_proba"].get("arknights"):
            user.additional["gacha_proba"]["arknights"] = [0, 2]
        six_statis, six_per = user.additional["gacha_proba"]["arknights"]
        gacha = ArknightsGacha(file=file, six_per=six_per, six_statis=six_statis)
        ops = gacha.generate_rank(10)
        data = simulate_ten_generate(ops[0])
        user.additional["gacha_proba"]["arknights"] = [gacha.six_statis, gacha.six_per]
        bot.data.update_user(user)
    else:
        gacha = ArknightsGacha(file=file)
        ops = gacha.generate_rank(10)
        data = simulate_ten_generate(ops[0])
    return await app.send_message(sender, MessageChain(Image(data_bytes=data)))
