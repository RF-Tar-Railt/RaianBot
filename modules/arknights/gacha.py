import itertools
import json
import math
import random
import re
from loguru import logger
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
    six_per: float
    five_per: float
    four_per: float
    operators: Dict[str, List[str]]  # 当期新 up 的干员不应该在里面
    up_limit: List[str]
    up_alert_limit: List[str]
    up_six_list: List[str]
    up_five_list: List[str]
    up_four_list: List[str]


class ArknightsGacha:
    six_statis: int
    six_per: int
    five_per: int
    four_per: int
    three_per: int
    data: ArknightsData

    color = {
        6: (0xFF, 0x7F, 0x27),  # ff7f27
        5: (0xFF, 0xC9, 0x0E),  # ffc90e
        4: (0x93, 0x19, 0x93),  # d8b3d8
        3: (0x09, 0xB3, 0xF7),  # 09b3f7
    }

    def __init__(
            self,
            six_per: int = 2,
            six_statis: int = 0,
            file: Optional[Union[str, Path]] = None,
    ):
        self.six_per = six_per
        self.five_per, self.four_per, self.three_per = 8, 50, 40
        if six_per > 2:
            for _ in range((six_per - 2) // 2):
                if self.three_per != 0:
                    self.three_per -= 2
                elif self.four_per != 0:
                    self.four_per -= 2
                elif self.five_per != 0:
                    self.five_per -= 2
        self.six_statis = six_statis
        if not file:
            file = Path(__file__).parent / "example_gacha.json"
        elif isinstance(file, str):
            file = Path(file)
            if not file.exists():
                raise FileNotFoundError
        self.file = file
        with file.open("r", encoding="UTF-8") as f_obj:
            self.data = json.load(f_obj)

    def update(self):
        if self.data["name"] != "常驻标准寻访" and self.data["six_per"] < 1:
            self.data['operators']['六'] += self.data['up_six_list']
            self.data['operators']['五'] += self.data['up_five_list']
            self.data['operators']['四'] += self.data['up_four_list']
        self.data['up_six_list'].clear()
        self.data['up_five_list'].clear()
        self.data['up_four_list'].clear()
        self.data['up_limit'].clear()
        self.data['up_alert_limit'].clear()

        result = httpx.get("https://ak.hypergryph.com/news.html").text
        if not result:
            logger.warning("明日方舟 获取公告出错")
            return
        dom = etree.HTML(result, etree.HTMLParser())
        activity_urls = dom.xpath(
            "//ol[@class='articleList' and @data-category-key='ACTIVITY']/li/a/@href"
        )
        up_chars = [[], [], []]
        for activity_url in activity_urls[:20]:  # 减少响应时间, 10个就够了
            activity_url = f"https://ak.hypergryph.com{activity_url}"
            result = httpx.get(activity_url).text
            if not result:
                logger.warning(f"明日方舟 获取公告 {activity_url} 出错")
                continue

            """因为鹰角的前端太自由了，这里重写了匹配规则以尽可能避免因为前端乱七八糟而导致的重载失败"""
            dom = etree.HTML(result, etree.HTMLParser())
            contents = dom.xpath(
                "//div[@class='article-content']/p/text() | //div[@class='article-content']/p/span/text() | //div["
                "@class='article-content']/div[@class='media-wrap image-wrap']/img/@src "
            )
            title = ""
            chars: List[str] = []
            for index, content in enumerate(contents):
                if not re.search("(.*)(寻访|复刻).*?开启", content):
                    continue
                title = re.split(r"[【】]", content)
                title = "".join(title[1:-1]) if "-" in title else title[1]
                lines = [contents[index - 2 + _] for _ in range(8)] + [""]
                for idx, line in enumerate(lines):
                    """因为 <p> 的诡异排版，所以有了下面的一段"""
                    if "★★" in line and ("%" in line or "%" in lines[idx + 1]):
                        chars.append(line) if ("★★" in line and "%" in line) else chars.append(line + lines[idx + 1])
                # pool_img = contents[index - 2]
                r"""两类格式：用/分割，用\分割；★+(概率)+名字，★+名字+(概率)"""
                for char in chars:
                    star = char.split("（")[0].count("★")
                    name = re.split(r"[（：]", char)[1] if "★（" not in char else re.split("（|）：", char)[2]
                    names = name.replace("\\", "/").split("/")
                    for name in names:
                        limit = False
                        if "[限定]" in name:
                            limit = True
                        name = name.replace("[限定]", "").strip()
                        zoom = 1
                        if match := re.search(
                            r"（在.*?以.*?(\d+).*?倍.*?）", char
                        ) or re.search(
                            r"（占.*?的.*?(\d+).*?%）", char
                        ):
                            zoom = float(match[1])
                            zoom = zoom / 100 if zoom > 10 else zoom
                        up_chars[6 - star].append([name, limit, zoom])
                break  # 这里break会导致个问题：如果一个公告里有两个池子，会漏掉下面的池子，比如 5.19 的定向寻访。但目前我也没啥好想法解决
            if not title:
                continue
            if title == self.data["name"]:
                return
            logger.debug(f"成功获取 当前up信息; 当前up池: {title}")
            self.data['name'] = title
            for char in up_chars[0]:
                if char[1]:
                    if not self.data['up_limit']:
                        self.data['up_limit'].append(char[0])
                    else:
                        self.data['up_alert_limit'].append(char[0])
                        continue
                else:
                    self.data['up_six_list'].append(char[0])
                self.data['six_per'] = char[2]
            for char in up_chars[1]:
                self.data['up_five_list'].append(char[0])
                self.data['five_per'] = char[2]
            for char in up_chars[2]:
                self.data['up_four_list'].append(char[0])
                self.data['four_per'] = char[2]

            with self.file.open("w", encoding="UTF-8") as f_obj:
                json.dump(self.data, f_obj, ensure_ascii=False, indent=4)
            return title

    def generate_rank(self, count: int = 1) -> List[List[ArknightsOperator]]:
        gacha_ranks: List[List[ArknightsOperator]] = []
        cache = []
        for i in range(1, count + 1):
            x = random_pick_big(
                "六五四三", [self.six_per, self.five_per, self.four_per, self.three_per]
            )
            ans = "".join(itertools.islice(x, 1))
            if ans != "六":
                self.six_statis += 1
                if self.six_statis > 50:
                    self.six_per += 2
                    if self.three_per != 0:
                        self.three_per -= 2
                    elif self.four_per != 0:
                        self.four_per -= 2
                    elif self.five_per != 0:
                        self.five_per -= 2
            else:
                self.six_statis = 0
                self.six_per = 2
                self.five_per, self.four_per, self.three_per = 8, 50, 40

            cache.append(self.generate_operator(ans))
            if i % 10 == 0:
                gacha_ranks.append(cache)
                cache = []
        if cache:
            gacha_ranks.append(cache)
        return gacha_ranks

    def generate_operator(self, rank: str) -> ArknightsOperator:
        card_list = self.data["operators"][rank].copy()
        if rank == "六":
            if (six_per := self.data["six_per"]) >= 1.0:
                return {"name": random.choice(self.data["up_six_list"]), "rarity": 6}
            up_res = random.choice(self.data["up_six_list"] + self.data["up_limit"])
            for c in self.data["up_alert_limit"]:
                card_list.extend([c for _ in range(5)])
            card_list.extend(
                [up_res for _ in range(int(len(card_list) * six_per / (1 - six_per)))]
            )
            random.shuffle(card_list)
            return {"name": random.choice(card_list), "rarity": 6}
        if rank == "五":
            if (five_per := self.data["five_per"]) >= 1.0:
                return {"name": random.choice(self.data["up_five_list"]), "rarity": 5}
            up_res = random.choice(self.data["up_five_list"])
            card_list.extend(
                [up_res for _ in range(int(len(card_list) * five_per / (1 - five_per)))]
            )
            random.shuffle(card_list)
            return {"name": random.choice(card_list), "rarity": 5}
        if rank == "四":
            if self.data["up_four_list"]:
                four_per = self.data["four_per"]
                up_res = random.choice(self.data["up_four_list"])
                card_list.extend(
                    [
                        up_res
                        for _ in range(int(len(card_list) * four_per / (1 - four_per)))
                    ]
                )
            return {"name": random.choice(card_list), "rarity": 4}
        return {"name": random.choice(card_list), "rarity": 3}

    def create_image(
            self,
            result: List[List[ArknightsOperator]],
            count: int = 1,
            relief: bool = False,
    ) -> bytes:
        tile = 20
        width_base = 720
        color_base = 0x40
        color_bases = (color_base, color_base, color_base)
        height = tile * int(math.ceil(count / 10) + 1) + 130
        img = Image.new("RGB", (width_base, height), color_bases)
        # 绘画对象
        draw = ImageDraw.Draw(img)
        font_base = ImageFont.truetype("simhei.ttf", 16)
        draw.text(
            (tile, tile), "博士小心地拉开了包的拉链...会是什么呢？", fill="lightgrey", font=font_base
        )

        pool = f"当前卡池:【{self.data['name']}】"
        draw.text(
            (width_base - font_base.getsize(pool)[0] - tile, tile),
            pool,
            fill="lightgrey",
            font=font_base,
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
                    (xi - i, yi - i, xi + i, yj + i), radius=16, fill=(r, r, r)
                )
                draw.rounded_rectangle(
                    (xj - i, yi - i, xj + i, yj + i), radius=16, fill=(r, r, r)
                )
            for i in range(4, 0, -1):
                r = (color_base // 4) * i
                draw.rounded_rectangle(
                    (xi - i, yi - i, xj + i, yi + i),
                    radius=20,
                    fill=(r, r, r, int(256 * 0.6)),
                )
                d = (0xFF - color_base) // 4
                r = 0xFF - i * d
                draw.rounded_rectangle(
                    (xi - i, yj - i, xj + i, yj + i),
                    radius=20,
                    fill=(r, r, r, int(256 * 0.8)),
                )
        for i, ots in enumerate(result):
            base = tile * 3
            if relief:
                draw.rounded_rectangle(
                    (
                        base,
                        tile * (i + 3) + 4,
                        base + tile * 3 * len(ots) - 2,
                        tile * (i + 4) + 3,
                    ),
                    radius=2,
                    fill=(color_base // 2, color_base // 2, color_base // 2),
                )
            for operator in ots:
                width = tile * 3
                length = len(operator["name"])
                length = max(length, 3)
                font_size = int(3 * font_base.size / length)
                font = font_base.font_variant(size=font_size)
                width_offset = (width - font.getsize(operator["name"])[0]) // 2
                height_offset = 1 + (tile - font.getsize(operator["name"])[1]) // 2

                draw.rounded_rectangle(
                    (base, tile * (i + 3) + 2, base + width - 2, tile * (i + 4)),
                    radius=2,
                    fill=self.color[operator["rarity"]],
                )
                draw.text(
                    (base + width_offset, tile * (i + 3) + height_offset),
                    operator["name"],
                    fill="#ffffff",
                    stroke_width=1,
                    stroke_fill=tuple(
                        int(i * 0.5) for i in self.color[operator["rarity"]]
                    ),
                    font=font,
                )
                base += width
        draw.text(
            (tile, height - 3 * tile + 10),
            f"博士已经抽取了{self.six_statis}次没有6星了" f"\n当前出6星的机率为 {self.six_per}%",
            fill="lightgrey",
            font=font_base,
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
logger.debug("basic image loaded.")
characters = {
    "先锋": Image.open(Path(__file__).parent / "resource" / "图标_职业_先锋_大图_白.png"),
    "近卫": Image.open(Path(__file__).parent / "resource" / "图标_职业_近卫_大图_白.png"),
    "医疗": Image.open(Path(__file__).parent / "resource" / "图标_职业_医疗_大图_白.png"),
    "术师": Image.open(Path(__file__).parent / "resource" / "图标_职业_术师_大图_白.png"),
    "狙击": Image.open(Path(__file__).parent / "resource" / "图标_职业_狙击_大图_白.png"),
    "特种": Image.open(Path(__file__).parent / "resource" / "图标_职业_特种_大图_白.png"),
    "辅助": Image.open(Path(__file__).parent / "resource" / "图标_职业_辅助_大图_白.png"),
    "重装": Image.open(Path(__file__).parent / "resource" / "图标_职业_重装_大图_白.png"),
}
logger.debug("careers image loaded.")
stars = {
    5: Image.open(Path(__file__).parent / "resource" / "稀有度_白_5.png"),
    4: Image.open(Path(__file__).parent / "resource" / "稀有度_白_4.png"),
    3: Image.open(Path(__file__).parent / "resource" / "稀有度_白_3.png"),
    2: Image.open(Path(__file__).parent / "resource" / "稀有度_白_2.png"),
}
logger.debug("stars image loaded.")
with (Path(__file__).parent / "resource" / "careers.json").open(
        "r", encoding="utf-8"
) as f:
    careers = json.load(f)
operators = {
    path.stem: Image.open(path)
    for path in (Path(__file__).parent / "resource" / "operators").iterdir()
}
logger.debug("operators image loaded.")


def simulate_ten_generate(ops: List[ArknightsOperator]):
    base = 20
    offset = 124
    l_offset = 14
    back_img = Image.open(Path(__file__).parent / "resource" / "back_image.png")
    for op in ops:
        name = op["name"]
        rarity = op["rarity"] - 1
        try:
            if name in operators:
                avatar: Image.Image = operators[name]
                logo: Image.Image = characters[careers[name]].resize(
                    (96, 96), Image.Resampling.LANCZOS
                )
            else:
                resp = httpx.get(f"https://prts.wiki/w/文件:半身像_{name}_1.png")
                root = etree.HTML(resp.text)
                sub = root.xpath(f'//img[@alt="文件:半身像 {name} 1.png"]')[0]
                avatar: Image.Image = Image.open(
                    BytesIO(
                        httpx.get(f"https://prts.wiki{sub.xpath('@src').pop()}").read()
                    )
                ).crop((20, 0, offset + 20, 360))
                with (
                        Path(__file__).parent / "resource" / "operators" / f"{name}.png"
                ).open("wb+") as _f:
                    avatar.save(
                        _f, format="PNG", quality=100, subsampling=2, qtables="web_high"
                    )
                resp1 = httpx.get(
                    f"https://prts.wiki/index.php?title={name}&action=edit"
                )
                root1 = etree.HTML(resp1.text)
                sub1 = root1.xpath('//textarea[@id="wpTextbox1"]')[0]
                cr = char_pat.search(sub1.text)[1]
                logo: Image.Image = characters[cr].resize(
                    (96, 96), Image.Resampling.LANCZOS
                )
                with (Path(__file__).parent / "resource" / "careers.json").open(
                        "w", encoding="utf-8"
                ) as jf:
                    careers[name] = cr
                    json.dump(careers, jf, ensure_ascii=False)
        except (ValueError, IndexError):
            resp = httpx.get("https://prts.wiki/w/文件:半身像_无_1.png")
            root = etree.HTML(resp.text)
            sub = root.xpath('//img[@alt="文件:半身像 无 1.png"]')[0]
            logo: Image.Image = characters["近卫"].resize(
                (96, 96), Image.Resampling.LANCZOS
            )
            avatar: Image.Image = Image.open(
                BytesIO(httpx.get(f"https://prts.wiki{sub.xpath('@src').pop()}").read())
            ).crop((20, 0, offset + 20, 360))

        s_size = stars[rarity].size
        star = stars[rarity].resize(
            (int(s_size[0] * 0.6), int(47 * 0.6)), Image.Resampling.LANCZOS
        )
        s_offset = (offset - int(star.size[0])) // 2

        if rarity == 5:
            back_img.paste(six_line_up, (base, 0), six_line_up)
            back_img.paste(six_line_down, (base, 720 - 256), six_line_down)
            back_img.paste(six_tail, (base, 0), six_tail)
            back_img.paste(
                six_tail.transpose(Image.Transpose.ROTATE_180),
                (base, 720 - 256),
                six_tail.transpose(Image.Transpose.ROTATE_180),
            )
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


if __name__ == "__main__":
    gacha = ArknightsGacha()
    # gacha.update()
    # ten = gacha.generate_rank(10)[0]
    # data = simulate_ten_generate(ten)
    data = gacha.gacha(100)
    io = BytesIO(data)
    Image.open(io, "r").show("test")
