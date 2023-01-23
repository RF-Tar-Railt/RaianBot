from __future__ import annotations

from typing import Literal
from graiax.text2img.playwright.renderer import HTMLRenderer
from graiax.text2img.playwright.converter import MarkdownConverter
from graiax.text2img.playwright.renderer import PageOption, ScreenshotOption
from graia.ariadne.util.async_exec import ParallelExecutor
from io import BytesIO
from PIL import Image, ImageFont, ImageDraw


def cut_text(
    origin: str,
    font: ImageFont.FreeTypeFont,
    chars_per_line: int,
):
    target = ""
    start_symbol = "[{<(【《（〈〖［〔“‘『「〝"
    end_symbol = ",.!?;:]}>)%~…，。！？；：】》）〉〗］〕”’～』」〞"
    line_width = chars_per_line * font.getlength("0")
    for i in origin.splitlines(False):
        if i == "":
            target += "\n"
            continue
        j = 0
        i = i.replace("\t", "  ")
        for ind, elem in enumerate(i):
            if i[j : ind + 1] == i[j:]:
                target += i[j : ind + 1] + "\n"
                continue
            elif font.getlength(i[j : ind + 1]) <= line_width:
                continue
            elif ind - j > 3:
                if i[ind] in end_symbol and i[ind - 1] != i[ind]:
                    target += i[j : ind + 1] + "\n"
                    j = ind + 1
                    continue
                elif i[ind] in start_symbol and i[ind - 1] != i[ind]:
                    target += i[j:ind] + "\n"
                    continue
            target += i[j:ind] + "\n"
            j = ind
    return target.rstrip()


async def render_markdown(
    md: str,
    width: int | None = None,
    height: int | None = None,
    factor: float = 1.5,
    itype: Literal["jpeg", "png"] = "jpeg",
    quality: int = 80,
):
    content = MarkdownConverter().convert(md)
    return await HTMLRenderer(
        screenshot_option=ScreenshotOption(type=itype, quality=quality, scale="device")
    ).render(
        content,
        extra_page_option=(
            PageOption(viewport={"width": width, "height": height}, device_scale_factor=factor)  # type: ignore
        ) if width is not None and height is not None else None
    )


async def create_image(
    text: str | list[str],
    font: str = "simhei.ttf",
    font_size: int = 20,
    cut: int = 80,
    mode: str = "RGB",
    background: tuple[int, int, int] | tuple[int, int, int, float] | str = "white",
) -> bytes:
    return await ParallelExecutor().to_thread(_create_image, text, font, font_size, cut, mode, background)


def _create_image(
    text: str | list[str],
    font: str,
    font_size: int = 20,
    cut: int = 80,
    mode: str = "RGB",
    background: tuple[int, int, int] | tuple[int, int, int, float] | str = "white",
) -> bytes:
    new_font = ImageFont.truetype(font, font_size)
    if isinstance(text, str):
        cut_str = cut_text(text, new_font, cut)
    else:
        cut_str = "\n".join(text)
    textx, texty = new_font.getsize_multiline(cut_str)
    image = Image.new(mode, (textx + 40, texty + 40), background)  # type: ignore
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), cut_str, font=new_font, fill="black")
    imageio = BytesIO()
    image.save(
        imageio,
        format="JPEG",
        quality=95,
        subsampling=2,
        qtables="web_high",
    )
    return imageio.getvalue()
