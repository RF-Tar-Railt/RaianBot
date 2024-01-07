from pathlib import Path
from typing import Union
from uuid import uuid4

from graia.amnesia.message import MessageChain
from avilla.core import Context, LocalFileResource
from avilla.core.elements import Text, Picture, Audio, Video, Face, File, Notice, NoticeAll, Unknown
from avilla.standard.qq.elements import MarketFace, FlashImage, Poke, Dice


def display(msg: MessageChain):
    res = []
    for elem in msg.content:
        if isinstance(elem, Text):
            res.append(elem.text)
        elif isinstance(elem, Picture):
            res.append("[图片]")
        elif isinstance(elem, Audio):
            res.append("[音频]")
        elif isinstance(elem, Video):
            res.append("[视频]")
        elif isinstance(elem, Face):
            res.append(f"[表情:{elem.name or elem.id}]")
        elif isinstance(elem, MarketFace):
            res.append(f"[商店表情:{elem.name or elem.id}]")
        elif isinstance(elem, FlashImage):
            res.append("[闪照]")
        elif isinstance(elem, File):
            res.append("[文件]")
        elif isinstance(elem, Notice):
            res.append(f"@{elem.display or elem.target.last_value}")
        elif isinstance(elem, NoticeAll):
            res.append("@全体成员")
        elif isinstance(elem, Poke):
            res.append("[戳一戳]")
        elif isinstance(elem, Dice):
            res.append("[骰子]")
        elif isinstance(elem, Unknown):
            res.append(f"{elem.type}")
        else:
            res.append(str(elem))
    return "".join(res)


async def serialize_message(msg: MessageChain, ctx: Context, image_path: Path):
    res = []
    msg = msg.include(Text, Picture, Face)
    for elem in msg:
        elem: Union[Text, Picture, Face]
        if isinstance(elem, Picture):
            name = uuid4().hex
            with (image_path / name).open('wb+') as img:
                img.write(await ctx.fetch(elem.resource))
            res.append({'type': 'Image', 'path': f"{(image_path / name).absolute()}"})
        elif isinstance(elem, Text):
            res.append({'type': 'Text', 'text': elem.text})
        elif isinstance(elem, Face):
            res.append({'type': 'Face', 'id': elem.id, 'name': elem.name})
    return res


def deserialize_message(content: list[dict]):
    res = []
    for elem in content:
        if elem['type'] == 'Text':
            res.append(Text(elem['text']))
        elif elem['type'] == 'Image':
            res.append(Picture(LocalFileResource(elem['path'])))
        elif elem['type'] == 'Face':
            res.append(Face(elem['id'], elem['name']))
    return MessageChain(res)
