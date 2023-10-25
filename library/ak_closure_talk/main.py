from __future__ import annotations

import ujson
from pathlib import Path
from urllib.parse import quote
import httpx
from loguru import logger

from library.ak_closure_talk.model import ClosureCharacter, ClosureChatArea, _ChatItem
from library.ak_closure_talk.exceptions import *

GITHUB_RAW_LINK = "https://raw.githubusercontent.com/ClosureTalk/closuretalk.github.io/master/{path}"


class ArknightsClosureStore:
    characters: set[ClosureCharacter]
    session: dict[str, ClosureChatArea]
    avatars: dict[str, dict[int, str]]

    def __init__(self, resource_path: str | None = None):
        if resource_path:
            self.base_path = Path(resource_path)
        else:
            self.base_path = Path(__file__).parent / "assets"
        with (self.base_path / "char.json").open("r", encoding="utf-8") as f:
            data = ujson.load(f)
        self.characters = {ClosureCharacter(**char) for char in data}
        self.characters.add(ClosureCharacter(
            "char_001_doctor",
            ["char_001_doctor"],
            {
                "en": "Doctor",
                "ja": "ドクター",
                "zh-cn": "博士",
                "zh-tw": "博士"
            },
            [],
            {
                "en": "Doctor",
                "ja": "ドクター",
                "zh-cn": "博士",
                "zh-tw": "博士"
            },
        ))
        self.avatars = {}
        self.session = {}

    def start(self, field: str, max_count: int = 1000):
        if field in self.session:
            raise SessionAlreadyExist("[ClosureTalk] 会话已经存在")
        self.session[field] = ClosureChatArea(max_count)
        self.avatars[field] = {}

    def end(self, field: str):
        self.avatars.pop(field, None)
        return self.session.pop(field, None)

    def add_char(self, field: str, uid: int, name: str):
        if field not in self.session:
            raise SessionNotExist("[ClosureTalk] 会话未存在")
        split = name.split("#")
        split = [split[0], split[1] if len(split) >= 2 else "1"]
        if not (characters := self.filter_character(split[0])):
            self.avatars[field][uid] = f"https://q2.qlogo.cn/headimg_dl?dst_uin={uid}&spec=640"
        else:
            character = characters[0]
            index = 0
            if split[1].isdigit() and 0 < int(split[1]) <= len(character.images):
                index = int(split[1]) - 1
            self.avatars[field][uid] = (
                #f"https://raw.githubusercontent.com/ClosureTalk/closuretalk.github.io/master/resources/ak/characters/{quote(character.images[index])}.webp"
                (self.base_path / "characters" / f"{character.images[index]}.webp").absolute().as_uri()
            )
            return character

    def add_content(self, content: str, field: str, uid: int):
        if field not in self.session:
            raise SessionNotExist("[ClosureTalk] 会话未存在")
        if uid not in self.avatars[field]:
            raise CharacterNotExist("[ClosureTalk] 角色未存在")
        if len(self.session[field].items) >= self.session[field].max_count:
            raise RecordMaxExceed("[ClosureTalk] 会话达到上限")
        self.session[field].items.append(_ChatItem(content, self.avatars[field][uid]))

    @staticmethod
    def _search(base: list[ClosureCharacter], key: str) -> list[ClosureCharacter]:
        key = key.lower()
        return list(
            filter(
                lambda character: any(
                    [
                        key == character.id.lower(),
                        (lambda x: any(key == y.lower() for y in x.values()))(character.names),
                        (lambda x: any(key == y.lower() for y in x))(character.searches),
                        (lambda x: any(key == y.lower() for y in x.values()))(character.short_names),
                    ]
                ),
                base,
            )
        )

    def filter_character(self, name: str) -> list[ClosureCharacter]:
        return self._search(list(self.characters), name)

    def export(self, field: str):
        if field not in self.session:
            raise SessionNotExist("[ClosureTalk] 会话未存在")
        return self.session[field].to_html()

    def download_resource(self):
        # https://github.com/ClosureTalk/closuretalk.github.io/raw/master/resources/ak/char.json
        char_path = self.base_path / "characters"
        char_path.mkdir(exist_ok=True, parents=True)
        total = len(self.characters)
        for char_index, character in enumerate(self.characters):
            for img_index, image in enumerate(character.images):
                image_path = f"{image}.webp"
                if (char_path / image_path).exists():
                    continue
                try:
                    resp = httpx.get(
                        GITHUB_RAW_LINK.format(path=f"resources/ak/characters/{quote(image)}.webp"),
                        proxies={
                            "http://": "http://127.0.0.1:7890",
                            "https://": "http://127.0.0.1:7890",
                        },
                        verify=False
                    )
                    with (char_path / image_path).open("wb+") as f:
                        f.write(resp.read())
                        name = image_path.split(".")[0]
                        logger.debug(f"[ClosureTalk] [{char_index} / {total}] 成功下载 {name}")
                except Exception as e:
                    logger.error(f"[ClosureTalk] [{char_index} / {total}] 下载 {image} 时出现错误：{e}")
        logger.debug("[ClosureTalk] 已下载资源")

if __name__ == "__main__":
    _store = ArknightsClosureStore()
    _store.download_resource()
