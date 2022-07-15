from arclet.alconna import Args
from arclet.alconna.graia import Alconna, Match, command
from graia.ariadne.message.element import Image
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.app import Ariadne


from app import RaianMain, Sender, Target, record
from modules.arknights import ArknightsGacha


@command(Alconna("(抽卡|寻访)", Args["count", int, 10], help_text="模拟方舟寻访 Example: $抽卡 300;"), send_error=True)
@record("抽卡")
async def draw(app: Ariadne, sender: Sender, target: Target, count: Match[int], bot: RaianMain):
    """模拟抽卡"""
    file = bot.config.plugin.get('gache', 'assets/data/gacha_arknights.json')
    count = min(max(count.result, 1), 300)
    if bot.data.exist(target.id):
        user = bot.data.get_user(target.id)
        if not user.additional.get('gacha_proba'):
            user.additional['gacha_proba'] = {'arknights': [0, 2]}
        elif not user.additional['gacha_proba'].get('arknights'):
            user.additional['gacha_proba']['arknights'] = [0, 2]
        six_statis, six_per = user.additional['gacha_proba']['arknights']
        gacha = ArknightsGacha(file=file, six_per=six_per, six_statis=six_statis)
        data = gacha.gacha(count)
        user.additional['gacha_proba']['arknights'] = [gacha.six_statis, gacha.six_per]
        bot.data.update_user(user)
    else:
        gacha = ArknightsGacha(file=file)
        data = gacha.gacha(count)
    return await app.send_message(sender, MessageChain(Image(data_bytes=data)))
