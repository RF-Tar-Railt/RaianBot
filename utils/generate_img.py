from typing import Union, List, Tuple

from graia.ariadne.util.async_exec import ParallelExecutor
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw


def cut_text(
    origin: str,
    font: ImageFont.FreeTypeFont,
    chars_per_line: int,
):
    target = ''
    start_symbol = '[{<(【《（〈〖［〔“‘『「〝'
    end_symbol = ',.!?;:]}>)%~…，。！？；：】》）〉〗］〕”’～』」〞'
    line_width = chars_per_line * font.getlength("0")
    for i in origin.splitlines(False):
        if i == '':
            target += '\n'
            continue
        j = 0
        i = i.replace("\t", "  ")
        for ind, elem in enumerate(i):
            if i[j: ind + 1] == i[j:]:
                target += i[j: ind + 1] + '\n'
                continue
            elif font.getlength(i[j: ind + 1]) <= line_width:
                continue
            elif ind - j > 3:
                if i[ind] in end_symbol and i[ind - 1] != i[ind]:
                    target += i[j: ind + 1] + '\n'
                    j = ind + 1
                    continue
                elif i[ind] in start_symbol and i[ind - 1] != i[ind]:
                    target += i[j:ind] + '\n'
                    continue
            target += i[j:ind] + '\n'
            j = ind
    return target.rstrip()


async def create_image(
        text: Union[str, List[str]],
        font: str = "simhei.ttf",
        font_size: int = 20,
        cut: int = 80,
        mode: str = "RGBA",
        background: Union[Tuple[int, int, int], Tuple[int, int, int, float], str] = 'white'
) -> bytes:
    return await ParallelExecutor().to_thread(_create_image, text, font, font_size, cut, mode, background)


def _create_image(
        text: Union[str, List[str]],
        font: str,
        font_size: int = 20,
        cut: int = 80,
        mode: str = "RGBA",
        background: Union[Tuple[int, int, int], Tuple[int, int, int, float], str] = 'white'
) -> bytes:
    new_font = ImageFont.truetype(font, font_size)
    if isinstance(text, str):
        cut_str = cut_text(text, new_font, cut)
    else:
        cut_str = "\n".join(text)
    textx, texty = new_font.getsize_multiline(cut_str)
    image = Image.new(mode, (textx + 40, texty + 40), background)  # type: ignore
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
