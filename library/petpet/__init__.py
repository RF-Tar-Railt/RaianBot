from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps
from PIL.Image import Image as PILImage
from PIL.Image import Resampling

frame_spec = [
    (27, 31, 86, 90),
    (22, 36, 91, 90),
    (18, 41, 95, 90),
    (22, 41, 91, 91),
    (27, 28, 86, 91),
]

squish_factor = [
    (0, 0, 0, 0),
    (-7, 22, 8, 0),
    (-8, 30, 9, 6),
    (-3, 21, 5, 9),
    (0, 0, 0, 0),
]

squish_translation_factor = [0, 20, 34, 21, 0]


frames_path = Path(__file__).parent / "assets"
frames = [frames_path.joinpath(f"frame{i}.png") for i in range(5)]


def _generate_per_frame(avatar: PILImage, index: int, squish=0, flip=False):
    spec = list(frame_spec[index])
    for j, s in enumerate(spec):
        spec[j] = int(s + squish_factor[index][j] * squish)
    hand = Image.open(frames[index])
    if flip:
        avatar = ImageOps.mirror(avatar)
    # 将头像放缩成所需大小
    avatar = avatar.resize(
        (int((spec[2] - spec[0]) * 1.2), int((spec[3] - spec[1]) * 1.2)), Resampling.LANCZOS
    ).quantize()
    # 并贴到空图像上
    gif_frame = Image.new("RGB", (112, 112), (255, 255, 255))
    gif_frame.paste(avatar, (spec[0], spec[1]))
    # 将手覆盖（包括偏移量）
    gif_frame.paste(hand, (0, int(squish * squish_translation_factor[index])), hand)
    # 返回
    return gif_frame


def generate(data: bytes, flip=False, squish=0) -> BytesIO:
    avatar = Image.open(BytesIO(data))
    gif_frames = [_generate_per_frame(avatar, i, squish=squish, flip=flip) for i in range(5)]

    image = BytesIO()
    gif_frames[0].save(
        image,
        format="GIF",
        append_images=gif_frames,
        save_all=True,
        duration=60,
        loop=0,
        quality=90,
        # optimize=False,
        qtables="web_high",
    )
    return image
