import itertools
import json
import math
import random
import re
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from typing import List, Optional, Union, TypedDict, Dict
from pathlib import Path
import httpx
from lxml import etree

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


class ArknightsGacha:
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
            file = Path(__file__).parent / 'example_gacha.json'
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
            count: int = 1,
            relief: bool = False
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
        draw.text((tile, tile), "博士小心地拉开了包的拉链...会是什么呢？", fill='lightgrey', font=font_base)

        pool = f"当前卡池:【{self.data['name']}】"
        draw.text(
            (width_base - font_base.getsize(pool)[0] - tile, tile),
            pool,
            fill='lightgrey', font=font_base
        )
        if relief:
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
                    radius=20,
                    fill=(r, r, r, int(256 * 0.6))
                )
                d = (0xff - color_base) // 4
                r = 0xff - i * d
                draw.rounded_rectangle(
                    (xi - i, yj - i, xj + i, yj + i),
                    radius=20,
                    fill=(r, r, r, int(256 * 0.8))
                )
        for i, ots in enumerate(operators):
            base = tile * 3
            if relief:
                draw.rounded_rectangle(
                    (base, tile * (i + 3) + 4, base + tile * 3 * len(ots) - 2, tile * (i + 4) + 3),
                    radius=2,
                    fill=(color_base // 2, color_base // 2, color_base // 2)
                )
            for operator in ots:
                width = tile * 3
                length = len(operator['name'])
                length = max(length, 3)
                font_size = int(3 * font_base.size / length)
                font = font_base.font_variant(size=font_size)
                width_offset = (width - font.getsize(operator['name'])[0]) // 2
                height_offset = 1 + (tile - font.getsize(operator['name'])[1]) // 2

                draw.rounded_rectangle(
                    (base, tile * (i + 3) + 2, base + width - 2, tile * (i + 4)),
                    radius=2,
                    fill=self.color[operator['rarity']]
                )
                draw.text(
                    (base + width_offset, tile * (i + 3) + height_offset),
                    operator['name'],
                    fill='#ffffff',
                    stroke_width=1, stroke_fill=tuple(int(i * 0.5) for i in self.color[operator['rarity']]),
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

    def gacha(self, count: int = 1, relief: bool = True):
        return self.create_image((self.generate_rank(count)), count, relief)


char_pat = re.compile(r"\|职业=(.+?)\n\|.+?")
six_bgi = Image.open(Path(__file__).parent / "resource" / "back_six.png")
five_bgi = Image.open(Path(__file__).parent / "resource" / "back_five.png")
four_bgi = Image.open(Path(__file__).parent / "resource" / "back_four.png")
low_bgi = Image.new("RGBA", (124, 360), (49, 49, 49))
six_tail = Image.open(Path(__file__).parent / "resource" / "six_02.png")

six_line = Image.open(Path(__file__).parent / "resource" / "six_01.png")
five_line = Image.open(Path(__file__).parent / "resource" / "five.png")
four_line = Image.open(Path(__file__).parent / "resource" / "four.png")

star_circle = Image.open(Path(__file__).parent / "resource" / "star_02.png")
enhance_five_line = Image.new("RGBA", (124, 720), (0x60, 0x60, 0x60, 0x50))
enhance_four_line = Image.new("RGBA", (124, 720), (132, 108, 210, 0x10))
brighter = ImageEnhance.Brightness(six_line)
six_line = brighter.enhance(1.5)
brighter = ImageEnhance.Brightness(four_line)
four_line = brighter.enhance(0.9)
six_line_up = six_line.crop((0, 0, six_line.size[0], 256))
six_line_down = six_line.crop((0, 256, six_line.size[0], 512))
five_line_up = five_line.crop((0, 0, five_line.size[0], 256))
five_line_down = five_line.crop((0, 256, five_line.size[0], 512))
four_line_up = four_line.crop((0, 0, four_line.size[0], 256))
four_line_down = four_line.crop((0, 256, four_line.size[0], 512))

characters = {
    "先锋": Image.open(
        Path(__file__).parent / "resource" / "图标_职业_先锋_大图_白.png"
    ),
    "近卫": Image.open(
        Path(__file__).parent / "resource" / "图标_职业_近卫_大图_白.png"
    ),
    "医疗": Image.open(
        Path(__file__).parent / "resource" / "图标_职业_医疗_大图_白.png"
    ),
    "术师": Image.open(
        Path(__file__).parent / "resource" / "图标_职业_术师_大图_白.png"
    ),
    "狙击": Image.open(
        Path(__file__).parent / "resource" / "图标_职业_狙击_大图_白.png"
    ),
    "特种": Image.open(
        Path(__file__).parent / "resource" / "图标_职业_特种_大图_白.png"
    ),
    "辅助": Image.open(
        Path(__file__).parent / "resource" / "图标_职业_辅助_大图_白.png"
    ),
    "重装": Image.open(
        Path(__file__).parent / "resource" / "图标_职业_重装_大图_白.png"
    ),
}
stars = {
    5: Image.open(
        Path(__file__).parent / "resource" / "稀有度_白_5.png"
    ),
    4: Image.open(
        Path(__file__).parent / "resource" / "稀有度_白_4.png"
    ),
    3: Image.open(
        Path(__file__).parent / "resource" / "稀有度_白_3.png"
    ),
    2: Image.open(
        Path(__file__).parent / "resource" / "稀有度_白_2.png"
    ),
}


def simulate_ten_generate(ops: List[ArknightsOperator]):
    base = 20
    offset = 124
    l_offset = 14
    back_img = Image.open(Path(__file__).parent / "resource" / "back_image.png")
    for op in ops:
        name = op['name']
        rarity = op['rarity'] - 1

        try:
            resp = httpx.get(f"https://prts.wiki/w/文件:半身像_{name}_1.png")
            root = etree.HTML(resp.text)
            sub = root.xpath(f'//img[@alt="文件:半身像 {name} 1.png"]')[0]
            resp1 = httpx.get(f"https://prts.wiki/index.php?title={name}&action=edit")
            root1 = etree.HTML(resp1.text)
            sub1 = root1.xpath('//textarea[@id="wpTextbox1"]')[0]

            logo: Image.Image = characters[char_pat.search(sub1.text)[1]].resize((96, 96), Image.Resampling.LANCZOS)
        except (ValueError, IndexError):
            resp = httpx.get("https://prts.wiki/w/文件:半身像_无_1.png")
            root = etree.HTML(resp.text)
            sub = root.xpath('//img[@alt="文件:半身像 无 1.png"]')[0]
            logo: Image.Image = characters["近卫"].resize((96, 96), Image.Resampling.LANCZOS)
        url = sub.xpath("@src").pop()
        avatar: Image.Image = Image.open(
            BytesIO(httpx.get(f"https://prts.wiki{url}").read())
        ).crop((20, 0, offset + 20, 360))

        s_size = stars[rarity].size
        star = stars[rarity].resize((int(s_size[0] * 0.6), int(47 * 0.6)), Image.Resampling.LANCZOS)
        s_offset = (offset - int(star.size[0])) // 2

        if rarity == 5:
            back_img.paste(six_line_up, (base, 0), six_line_up)
            back_img.paste(six_line_down, (base, 720 - 256), six_line_down)
            back_img.paste(six_tail, (base, 0), six_tail)
            back_img.paste(six_tail.transpose(Image.Transpose.ROTATE_180), (base, 720 - 256),
                           six_tail.transpose(Image.Transpose.ROTATE_180))
            basei = six_bgi.copy()
        elif rarity == 4:
            back_img.paste(enhance_five_line, (base, 0), enhance_five_line)
            back_img.paste(five_line_up, (base, 0), five_line_up)
            back_img.paste(five_line_down, (base, 720 - 256), five_line_down)
            basei = five_bgi.copy()
        elif rarity == 3:
            back_img.paste(enhance_four_line, (base, 0), enhance_four_line)
            back_img.paste(four_line_up, (base, 0), four_line_up)
            back_img.paste(four_line_down, (base, 720 - 256), four_line_down)
            back_img.paste(star_circle, (base - 2, 180 - 64), star_circle)
            basei = four_bgi.copy()
        else:
            basei = low_bgi.copy()
        size = avatar.size
        avatar.thumbnail(size)
        basei.paste(avatar, (0, 0), avatar)
        back_img.paste(basei, (base, 180))
        s_size = star.size
        star.thumbnail(s_size)
        back_img.paste(star, (base + s_offset, 166), star)
        l_size = logo.size
        logo.thumbnail(l_size)
        back_img.paste(logo, (base + l_offset, 492), logo)
        base += offset
    imageio = BytesIO()
    back_img.save(
        imageio,
        format="PNG",
        quality=80,
        subsampling=2,
        qtables="web_high",
    )
    return imageio.getvalue()


if __name__ == '__main__':
    gacha = ArknightsGacha()
    ten = gacha.generate_rank(10)[0]
    data = simulate_ten_generate(ten)
    # data = gacha.gacha(30)
    io = BytesIO(data)
    Image.open(io, "r").show("test")
    gacha = ArknightsGacha()
    ten = gacha.generate_rank(10)[0]
    data = simulate_ten_generate(ten)
    # data = gacha.gacha(30)
    io = BytesIO(data)
    Image.open(io, "r").show("test")
