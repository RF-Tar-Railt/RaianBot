import json
from pathlib import Path
from datetime import datetime
from random import Random
from typing import Optional, TypedDict, List, Dict


class Information(TypedDict):
    career: List[Dict]
    organize: List[str]
    homeland: List[str]
    race: List[str]
    phy_exam_evaul: List[str]


class RandomOperator:
    rand_operator_dict: Information

    def __init__(self, path: Optional[str] = None):
        path = Path(path) if path else Path(__file__).parent / "operator_template.json"
        with path.open("r+", encoding='utf-8') as f:
            self.rand_operator_dict = json.load(f)

    def generate(self, name: str) -> str:
        rand = Random()
        count = sum(ord(char) for char in name)
        now = datetime.now()
        rand.seed(count + (now.day * now.month) + now.year)

        career_dict = rand.choice(self.rand_operator_dict['career'])
        career_name = career_dict['name']
        career_info_dict = rand.choice(career_dict['info'])

        sex = '男' if rand.randint(1, 2) == 1 else '女'
        career_detail = career_info_dict['name']
        level = rand.randint(3, 6)
        cost = career_info_dict['cost_basic'] + level - (2 if rand.randint(0, 4) >= 2 else rand.randint(0, 1))
        attack_speed = career_info_dict['attack_speed']
        block = career_info_dict['block']
        talent = career_info_dict['talent']
        tags = career_info_dict['tags']['static'] + rand.choice(career_info_dict['tags']['optional'])
        infect = "参照医学检测报告，确认为" + ('感染者。' if rand.randint(0, 10) > 5 else '非感染者。')
        race = rand.choice(self.rand_operator_dict['race'])
        homeland = rand.choice(self.rand_operator_dict['homeland'])
        organize = rand.choice(self.rand_operator_dict['organize'])
        if organize.endswith("homeland"):
            organize = rand.choice(self.rand_operator_dict['homeland'])
        height = rand.randint(0, 25) + (165 if sex == '男' else 155)
        fight_exp = rand.randint(0, 6) if rand.randint(0, 10) > 2 else rand.randint(6, 20)

        return "\n".join([
            f"{name}",
            f"{'★' * level}",
            f"【性别】{sex}",
            f"【职业】{career_name}-{career_detail}",
            f"【初始费用】{cost}",
            f"【阻挡数】{block}",
            f"【攻击速度】{attack_speed}",
            f"【特性】{talent}",
            f"【标签】{tags}",
            "\n",
            f"【种族】{race}",
            f"【身高】{height} cm",
            f"【出生地】{homeland}",
            f"【所属阵营】{organize}",
            f"【战斗经验】{'无' if fight_exp == 0 else f'{fight_exp}年'}"
            "\n",
            f"【矿石病感染情况】{infect}",
            f"【物理强度】{rand.choice(self.rand_operator_dict['phy_exam_evaul'])}",
            f"【战场机动】{rand.choice(self.rand_operator_dict['phy_exam_evaul'])}",
            f"【生理耐受】{rand.choice(self.rand_operator_dict['phy_exam_evaul'])}",
            f"【战术规划】{rand.choice(self.rand_operator_dict['phy_exam_evaul'])}",
            f"【战斗技巧】{rand.choice(self.rand_operator_dict['phy_exam_evaul'])}",
            f"【源石技艺适应性】{rand.choice(self.rand_operator_dict['phy_exam_evaul'])}"
        ])
