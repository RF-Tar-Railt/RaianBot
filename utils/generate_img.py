from typing import Union, List

from graia.ariadne.util.async_exec import ParallelExecutor
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw

import re
import string


def get_cut_str(this_str, cut):
    """
    自动断行，用于 Pillow 等不会自动换行的场景
    """
    punc = """，,、。.？?）》】“"‘'；;：:！!·`~%^& """
    si = 0
    i = 0
    next_str = this_str
    str_list = []

    while re.search(r"\n\n\n\n\n", next_str):
        next_str = re.sub(r"\n\n\n\n\n", "\n", next_str)
    for s in next_str:
        si += 1 if s in string.printable else 2
        i += 1
        if next_str == "":
            break
        elif next_str[0] == "\n":
            next_str = next_str[1:]
        elif s == "\n":
            str_list.append(next_str[: i - 1])
            next_str = next_str[i - 1:]
            si = 0
            i = 0
            continue
        if si > cut:
            try:
                if next_str[i] in punc:
                    i += 1
            except IndexError:
                str_list.append(next_str)
                return str_list
            str_list.append(next_str[:i])
            next_str = next_str[i:]
            si = 0
            i = 0
    str_list.append(next_str)
    i = 0
    non_wrap_str = []
    for p in str_list:
        if p == "":
            break
        elif p[-1] == "\n":
            p = p[:-1]
        non_wrap_str.append(p)
        i += 1
    return non_wrap_str


def _get_cut_str(this_str, cut):
    si = 0
    i = 0
    cut_str = ""
    for s in this_str:
        si += 2 if "\u4e00" <= s <= "\u9fff" else 1
        i += 1
        if si <= cut:
            cut_str = this_str
        else:
            cut_str = this_str[:i] + "...."
            break
    return cut_str


async def create_image(
        text: Union[str, List[str]],
        font: str = "simhei.ttf",
        font_size: int = 20,
        cut: int = 80,
        mode: str = "RGBA"
) -> bytes:
    return await ParallelExecutor().to_thread(_create_image, text, font, font_size, cut, mode)


def _create_image(
    text: Union[str, List[str]],
    font: str,
    font_size: int = 20,
    cut: int = 80,
    mode: str = "RGBA"
) -> bytes:
    cut_str = "\n".join(get_cut_str(text, cut))
    new_font = ImageFont.truetype(font, font_size)
    textx, texty = new_font.getsize_multiline(cut_str)
    image = Image.new(mode, (textx + 40, texty + 40), 'white')  # type: ignore
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), cut_str, font=new_font, fill='black')
    imageio = BytesIO()
    image.save(
        imageio,
        format="PNG",
        quality=90,
        subsampling=2,
        qtables="web_high",
    )
    return imageio.getvalue()

