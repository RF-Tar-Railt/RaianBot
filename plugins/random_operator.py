import random
import json
from datetime import datetime
from typing import Union
from arclet.alconna import Args, Empty
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, At
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from config import bot_config
from utils.generate_img import create_image

channel = Channel.current()

random_ope = Alconna(
    "测试干员", Args["name":[str, At]:Empty],
    headers=bot_config.command_prefix,
    help_text="依据名字测试你会是什么干员 Example: .测试干员 海猫;",
)

json_filename = "data/static/random_operator_infomation.json"
with open(json_filename, 'r', encoding='UTF-8') as f_obj:
    random_operator_dict = json.load(f_obj)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=random_ope, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def test2(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    event = result.source
    arp = result.result
    if arp.name:
        if isinstance(arp.name, At):
            target = arp.name.display
            if not target:
                target = (await app.getUserProfile(arp.name.target)).nickname
        else:
            target = arp.name
    else:
        target = event.sender.name
    return await app.sendMessage(
        sender, MessageChain.create(Image(data_bytes=(await generate_random_operator(target))))
    )


async def generate_random_operator(this_str: str) -> bytes:
    count = 0
    for char in this_str:
        count += ord(char)
    now = datetime.now()
    random.seed(count + (now.day * now.month) + now.year)

    career_dict = random.choice(random_operator_dict['career'])
    career_name = career_dict['name']
    career_info_dict = random.choice(career_dict['info'])

    sex = '男' if random.randint(1, 2) == 1 else '女'
    career_detail = career_info_dict['name']
    level = random.randint(3, 6)
    cost = career_info_dict['cost_basic'] + level - (2 if random.randint(0, 4) >= 2 else random.randint(0, 1))
    attack_speed = career_info_dict['attack_speed']
    block = career_info_dict['block']
    talent = career_info_dict['talent']
    tags = career_info_dict['tags']['static'] + random.choice(career_info_dict['tags']['optional'])
    infect = "参照医学检测报告，确认为" + ('感染者。' if random.randint(0, 10) > 5 else '非感染者。')
    race = random.choice(random_operator_dict['race'])
    homeland = random.choice(random_operator_dict['homeland'])
    organize = random.choice(random_operator_dict['organize'])
    height = random.randint(0, 25) + (165 if sex == '男' else 155)
    fight_exp = random.randint(0, 6) if random.randint(0, 10) > 2 else random.randint(6, 20)

    describe = "\n".join([
        f"{this_str}",
        f"{'★' * level}",
        f"【性别】{sex}",
        f"【职业】{career_name}-{career_detail}",
        f"【初始费用】{cost}",
        f"【阻挡数】{block}",
        f"【攻击速度】{attack_speed}",
        f"【特性】{talent}",
        f"【标签】{tags}",
        f"\n",
        f"【种族】{race}",
        f"【身高】{height} cm",
        f"【出生地】{homeland}",
        f"【所属阵营】{organize}",
        f"【战斗经验】{'无' if fight_exp == 0 else str(fight_exp) + '年'}"
        f"\n",
        f"【矿石病感染情况】{infect}",
        f"【物理强度】{random.choice(random_operator_dict['phy_exam_evaul'])}",
        f"【战场机动】{random.choice(random_operator_dict['phy_exam_evaul'])}",
        f"【生理耐受】{random.choice(random_operator_dict['phy_exam_evaul'])}",
        f"【战术规划】{random.choice(random_operator_dict['phy_exam_evaul'])}",
        f"【战斗技巧】{random.choice(random_operator_dict['phy_exam_evaul'])}",
        f"【源石技艺适应性】{random.choice(random_operator_dict['phy_exam_evaul'])}"
    ])
    return await create_image(describe, cut=120)
