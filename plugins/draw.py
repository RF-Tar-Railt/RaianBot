import json
import random
from datetime import datetime
from arclet.alconna.graia import Alconna
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Source
from graia.ariadne.app import Ariadne

from app import RaianMain, Sender, Target, command, record
from modules.rand import random_pick_small

json_filename = "assets/data/draw_poetry.json"
with open(json_filename, 'r', encoding='UTF-8') as f_obj:
    draw_poetry = json.load(f_obj)['data']


@record("抽签")
@command(Alconna("抽签", help_text="进行一次抽签, 可以解除"))
async def draw(app: Ariadne, sender: Sender, target: Target, source: Source, bot: RaianMain):
    """每日运势抽签"""
    today = datetime.now().day
    if not bot.data.exist(target.id):
        return await app.send_message(sender, MessageChain("您还未找我签到~"), quote=source.id)
    user = bot.data.get_user(target.id)
    if not user.additional.get('draw_info'):
        user.additional['draw_info'] = [-1, "无"]
    local_day, draw_ans = user.additional['draw_info']
    if today != local_day:
        some_list = [0, 1, 2, 3, 4, 5, 6]  # 大凶，凶，末吉，小吉，中吉，吉，大吉
        probabilities = [0.09, 0.25, 0.06, 0.07, 0.11, 0.25, 0.17]
        draw_num = random_pick_small(some_list, probabilities)
        poetry_data = draw_poetry[draw_num]
        draw_ans = poetry_data['type']
        text = poetry_data['poetry'][random.randint(1, poetry_data['count']) - 1]
        user.additional['draw_info'] = [today, draw_ans]
        bot.data.update_user(user)
        return await app.send_message(
            sender, MessageChain(f"您今日的运势抽签为：{draw_ans}\n{text}"),
            quote=source.id
        )
    bot.data.update_user(user)
    return await app.send_message(
        sender, MessageChain(f"您今天已经抽过签了哦,运势为{draw_ans}"),
        quote=source.id
    )


@command(Alconna("解签", help_text="解除上一次的抽签"))
async def draw(app: Ariadne, sender: Sender, target: Target, source: Source, bot: RaianMain):
    if not bot.data.exist(target.id):
        return await app.send_message(sender, MessageChain("您还未找我签到~"), quote=source.id)
    user = bot.data.get_user(target.id)
    if not (info := user.additional.get('draw_info')) or info[0] == -1:
        return await app.send_message(sender, MessageChain("您今日还未抽签~"), quote=source.id)
    info[0] = -1
    return await app.send_message(sender, MessageChain("您已成功解签"), quote=source.id)
