import base64
import hashlib
from io import BytesIO
from pathlib import Path
from typing import Union

import ujson
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Face, Image, Plain
from loguru import logger
from PIL import Image as PILImage

cache_dir_root = Path(input("输入当前缓存数据目录: >>>"))
if not cache_dir_root.exists():
    logger.warning("未知的目录")
    exit(1)

if (gd := cache_dir_root / "groups_data.json").exists():
    logger.info("处理群组数据中。。。")
    with gd.open("r+", encoding="utf-8") as f:
        data: dict = ujson.load(f)
    if data.get("version", 1) < 2:
        for gid, group in data.items():
            logger.debug(f"当前处理群组: {gid}")
            if add := group.get("additional", {}):
                add: dict
                if "mute" in add:
                    add["mute"] = [add["mute"]]
                if "weibo_followers" in add:
                    add["weibo_followers"] = [add["weibo_followers"]]
                if "roles" in add:
                    add["roles"] = [add["roles"]]
            logger.debug(f"处理群组 {gid} 完成")
        with gd.open("w", encoding="utf-8") as f:
            ujson.dump({"version": 2, "data": data}, f, ensure_ascii=False, indent=2)
    logger.success("处理群组数据完成")

if (ud := cache_dir_root / "users_data.json").exists():
    logger.info("处理用户数据中。。。")
    with ud.open("r+", encoding="utf-8") as f:
        data: dict = ujson.load(f)
    if data.get("version", 1) < 2:
        for uid, user in data.items():
            logger.debug(f"当前处理用户: {uid}")
            if add := user.get("additional", {}):
                add: dict
                if "gacha_proba" in add:
                    add["arkgacha_proba"] = add["gacha_proba"]["arknights"]
                    del add["gacha_proba"]
            logger.debug(f"处理用户 {uid} 完成")
        with ud.open("w", encoding="utf-8") as f:
            ujson.dump({"version": 2, "data": data}, f, ensure_ascii=False, indent=2)
    logger.success("处理用户数据完成")


def _deserialize_message(msg: MessageChain, path: Path):
    res = []
    for elem in msg:
        elem: Union[Plain, Image, Face]
        if isinstance(elem, Image):
            _img = base64.b64decode(elem.base64)
            _hash = hashlib.md5(_img).hexdigest()
            _pimg: PILImage.Image = PILImage.open(BytesIO(_img))
            with (path / f"{_hash}.{_pimg.format}").open("wb+") as img:
                img.write(_img)
            res.append({"type": "Image", "path": f"{(path / f'{_hash}.{_pimg.format}').absolute()}"})
        else:
            res.append(elem.dict())
    return ujson.dumps(res, ensure_ascii=False, indent=0)


lr_dir = cache_dir_root / "plugins" / "learn_repeat"
if lr_dir.exists():
    logger.info("处理学习回复数据中。。。")
    img_path = lr_dir / "image"
    img_path.mkdir(exist_ok=True)
    for file in lr_dir.iterdir():
        if file.is_dir():
            continue
        logger.debug(f"当前处理数据: {file}")
        with file.open("r+", encoding="utf-8") as f_obj:
            _data = ujson.load(f_obj)
        for key in _data.keys():
            content = _data[key]["content"]
            if _data[key].get("json"):
                if "path" not in content:
                    send = MessageChain.parse_obj(ujson.loads(content))
                    _data[key]["content"] = _deserialize_message(send, img_path)
            else:
                send = MessageChain.from_persistent_string(content)
                _data[key]["content"] = _deserialize_message(send, img_path)
                _data[key]["json"] = True
        logger.debug(f"处理数据 {file} 完成")
        with file.open("w+", encoding="utf-8") as fo:
            ujson.dump(_data, fo, ensure_ascii=False, indent=2)
    logger.success("处理学习回复完毕")

logger.info("数据处理完成，按任意键退出。")
input()
