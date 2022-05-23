import itertools
import json
import math
import random
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional, Union, TypedDict, Dict
from pathlib import Path

from modules.rand import random_pick_big


class ArknightsOperator(TypedDict):
    name: str
    rarity: int


class ArknightsData(TypedDict):
    name: str
    type: str  # "default", "unite", "limit"
    operators: Dict[str, List[str]]  # 当期新 up 的干员不应该在里面
    up_five_list: List[str]
    up_six_list: List[str]


class GArknights:
    six_statis: int
    six_per: int
    five_per: int
    four_per: int
    three_per: int
    data: ArknightsData

    color = {
        6: (0xff, 0x7f, 0x27),  # ff7f27
        5: (0xff, 0xc9, 0x0e),  # ffc90e
        4: (0x93, 0x19, 0x93),  # d8b3d8
        3: (0x09, 0xb3, 0xf7)  # 09b3f7
    }

    def __init__(
            self,
            six_per: int = 2,
            six_statis: int = 0,
            file: Optional[Union[str, Path]] = None
    ):
        self.six_per = six_per
        self.five_per, self.four_per, self.three_per = 8, 50, 40
        self.six_statis = six_statis
        if not file:
            file = Path(__file__).parent / 'Arknights.json'
        elif isinstance(file, str):
            file = Path(file)
            if not file.exists():
                raise FileNotFoundError
        with file.open("r", encoding='UTF-8') as f_obj:
            self.data = json.load(f_obj)

    def generate_rank(self, count: int = 1) -> List[List[ArknightsOperator]]:
        gacha_ranks: List[List[ArknightsOperator]] = []
        cache = []
        for i in range(1, count + 1):
            x = random_pick_big(
                '六五四三',
                [self.six_per, self.five_per, self.four_per, self.three_per]
            )
            ans = ''.join(itertools.islice(x, 1))
            if ans != '六':
                self.six_statis += 1
                if self.six_statis > 50:
                    self.six_per += 2
            else:
                self.six_statis = 0
                self.six_per = 2
            cache.append(self.generate_operator(ans))
            if i % 10 == 0:
                gacha_ranks.append(cache)
                cache = []
        if cache:
            gacha_ranks.append(cache)
        return gacha_ranks

    def generate_operator(self, rank: str) -> ArknightsOperator:
        six_percent = 50
        five_percent = 50
        if self.data['type'] == "limit":
            six_percent = 30
        if self.data['type'] == "unite":
            six_percent = 0
            five_percent = 0
        card_list = self.data['operators'][rank]
        res = random.choice(card_list)
        if rank == '六':
            up_res = random.choice(self.data['up_six_list'])
            if random.randint(1, 100) > six_percent:
                res = up_res
            return {"name": res, "rarity": 6}
        if rank == '五':
            up_res = random.choice(self.data['up_five_list'])
            if random.randint(1, 100) > five_percent:
                res = up_res
            return {"name": res, "rarity": 5}
        if rank == '四':
            return {"name": res, "rarity": 4}
        return {"name": res, "rarity": 3}

    def create_image(
            self,
            operators: List[List[ArknightsOperator]],
            count: int = 1
    ) -> bytes:
        tile = 20
        width_base = 720
        color_base = 0x40
        color_bases = (color_base, color_base, color_base)
        height = tile * int(math.ceil(count / 10) + 1) + 130
        img = Image.new("RGB", (width_base, height), color_bases)
        # 绘画对象
        draw = ImageDraw.Draw(img)
        font_base = ImageFont.truetype('simhei.ttf', 16)
        draw.text(
            (tile, tile),
            f"博士小心地拉开了包的拉链...会是什么呢？",
            fill='lightgrey', font=font_base
        )
        pool = f"当前卡池:【{self.data['name']}】"
        draw.text(
            (width_base - font_base.getsize(pool)[0] - tile, tile),
            pool,
            fill='lightgrey', font=font_base
        )
        xi = 2 * tile
        yi = 2 * tile + 4
        xj = width_base - (2 * tile)
        yj = tile * (int(math.ceil(count / 10)) + 4)
        for i in range(3, 0, -1):
            d = int(color_base * 0.2) // 4
            r = int(color_base * 0.8) + i * d
            draw.rounded_rectangle(
                (xi - i, yi - i, xi + i, yj + i),
                radius=16,
                fill=(r, r, r)
            )
            draw.rounded_rectangle(
                (xj - i, yi - i, xj + i, yj + i),
                radius=16,
                fill=(r, r, r)
            )
        for i in range(4, 0, -1):
            r = ((color_base // 4) * i)
            draw.rounded_rectangle(
                (xi - i, yi - i, xj + i, yi + i),
                radius=16,
                fill=(r, r, r, int(256 * 0.6))
            )
            r = ((0xff - color_base) // 4) * (5 - i)
            draw.rounded_rectangle(
                (xi - i, yj - i, xj + i, yj + i),
                radius=16,
                fill=(r, r, r, int(256 * 0.8))
            )
        for i, ots in enumerate(operators):
            base = tile * 3
            for operator in ots:
                width = tile * 3
                length = len(operator['name'])
                if length < 3:
                    length = 3
                font_size = int(3 * font_base.size / length)
                font = font_base.font_variant(size=font_size)
                width_offset = (width - font.getsize(operator['name'])[0]) // 2
                height_offset = 1 + (tile - font.getsize(operator['name'])[1]) // 2
                draw.rounded_rectangle(
                    (base, tile * (i + 3) + 2, base + width - 2, tile * (i + 4)),
                    radius=7,
                    fill=self.color[operator['rarity']]
                )
                draw.text(
                    (base + width_offset, tile * (i + 3) + height_offset),
                    operator['name'],
                    fill='white',
                    stroke_width=1, stroke_fill='#404040',
                    font=font
                )
                base += width
        draw.text(
            (tile, height - 3 * tile + 10),
            f"博士已经抽取了{self.six_statis}次没有6星了"
            f"\n当前出6星的机率为 {self.six_per}%",
            fill='lightgrey', font=font_base
        )
        imageio = BytesIO()
        img.save(
            imageio,
            format="PNG",
            quality=90,
            subsampling=2,
            qtables="web_high",
        )
        return imageio.getvalue()

    def gacha(self, count: int = 1):
        return self.create_image((self.generate_rank(count)), count)


if __name__ == '__main__':
    gacha = GArknights()
    data = gacha.gacha(300)
    io = BytesIO(data)
    Image.open(io, "r").show("test")
