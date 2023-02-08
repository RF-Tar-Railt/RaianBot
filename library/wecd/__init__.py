from io import BytesIO
from pathlib import Path
from PIL import Image, ImageFont, ImageDraw

ENG_FONT = ImageFont.truetype(
    str(Path(__file__).parent / "assets" / "fonts" / "Alte DIN 1451 Mittelschrift gepraegt Regular.ttf"), 36
)
CHN_FONT = ImageFont.truetype(
    str(Path(__file__).parent / "assets" / "fonts" / "字魂59号-创粗黑.ttf"), 36
)
COUNTING_FONT = ImageFont.truetype(
    str(Path(__file__).parent / "assets" / "fonts" / "Alte DIN 1451 Mittelschrift gepraegt Regular.ttf"), 110
)
BOTTOM_FONT = ImageFont.truetype(
    str(Path(__file__).parent / "assets" / "fonts" / "Alte DIN 1451 Mittelschrift gepraegt Regular.ttf"), 18
)

def getsize(txt: str, font: ImageFont.FreeTypeFont):
    bbox = font.getbbox(txt, "L")
    return bbox[2] - bbox[0], bbox[3] - bbox[1]

def gen_counting_down(
    top_text: str, start_text: str, counting: int, end_text: str, bottom_text: str, rgba: bool = False
) -> Image.Image:
    top_size = getsize(top_text, CHN_FONT)
    start_size = getsize(start_text, CHN_FONT)
    counting_size = getsize(str(counting), COUNTING_FONT)
    end_size = getsize(end_text, CHN_FONT)
    bottom_texts = bottom_text.split("\n")
    bottom_size = max(getsize(t, BOTTOM_FONT)[0] for t in bottom_texts), len(bottom_texts) * 26
    top_over_width = top_size[0] - start_size[0] - 20
    top_over_width = max(top_over_width, 0)
    start_over_width = start_size[0] - top_size[0] if start_size[0] >= top_size[0] else 0
    width = max([
        max(top_size[0], start_size[0]) + 20 + counting_size[0] + end_size[0],
        top_over_width + bottom_size[0]
    ]) + 60
    height = 104 + 46 * len(bottom_texts) + 40
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0)) if rgba else Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    rec_start = 20 if start_over_width > 0 else top_over_width
    rec_box = (rec_start + 30, 70, rec_start + 34, 150)
    start_start = rec_start + 40
    count_start = rec_start + 46 + start_size[0] if start_over_width > 0 else start_over_width + top_size[0] + 30
    top_start = count_start - top_size[0] - 6 if start_over_width > 0 else 20
    if start_over_width == 0 and top_over_width == 0:
        count_start = start_start + 6 + start_size[0]
        top_start = start_start
    end_start = count_start + counting_size[0] + 6 if start_over_width > 0 else top_size[0] + 40 + counting_size[0]
    if start_over_width == 0 and top_over_width == 0:
        end_start += 8

    draw.text((top_start, 20), top_text, fill="#FFFFFF", font=CHN_FONT)
    draw.text((count_start, -5), str(counting), fill="#FF0000", font=COUNTING_FONT)
    draw.text((start_start, 66), start_text, fill="#FFFFFF", font=CHN_FONT)
    draw.text((end_start, 66), end_text, fill="#FFFFFF", font=CHN_FONT)
    draw.rectangle(rec_box, fill="#FF0000")
    for i, t in enumerate(bottom_texts):
        draw.text((rec_start + 44, 106 + i * 24), t, fill="#FFFFFF", font=BOTTOM_FONT)
    return img


def gen_gif(
    top_text: str, start_text: str, counting: int, end_text: str, bottom_text: str, rgba: bool = False
) -> bytes:
    frames = [
        gen_counting_down(
            top_text, start_text, i, end_text, bottom_text, rgba
        )
        for i in range(counting, -1, -1)
    ]
    bytesio = BytesIO()
    frames[0].save(
        bytesio,
        format="GIF",
        append_images=frames,
        save_all=True,
        duration=1,
        loop=0,
        quality=90,
        # optimize=False,
        qtables="web_high",
    )
    return bytesio.getvalue()

if __name__ == '__main__':
    gen_counting_down(
        "中文内容",
        "还有(剩余)",
        1,
        "单位",
        "english content",
    ).show("test")