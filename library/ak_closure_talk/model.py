from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ui import wrap_text

from lxml.html import builder, tostring
from lxml.html.builder import CLASS


@dataclass(unsafe_hash=True)
class ClosureCharacter:
    id: str = field(hash=True)
    images: list[str] = field(hash=False)
    names: dict[str, str] = field(hash=False)
    searches: list[str] = field(hash=False)
    short_names: dict[str, str] = field(hash=False)


ASSETS_PATH = Path(__file__).parent / "assets"


def _escape(string: str) -> str:
    return string.replace("#", ":")


@dataclass(unsafe_hash=True)
class _ChatContent:
    content: str

    def elem(self):
        return builder.DIV(
            builder.DIV(*wrap_text(self.content, hyperlink=False), CLASS("akn-content-text")),
            CLASS("akn-content"),
        )


@dataclass(unsafe_hash=True)
class _ChatAvatar:
    src: str

    def elem(self):
        return builder.DIV(builder.IMG(src=self.src), CLASS("akn-avatar"))


class _ChatItem:
    content: _ChatContent
    avatar: _ChatAvatar

    def __init__(self, content: str, avatar_src: str):
        self.content = _ChatContent(content)
        self.avatar = _ChatAvatar(avatar_src)

    def elem(self):
        return builder.DIV(self.avatar.elem(), self.content.elem(), CLASS("akn-item"))


@dataclass
class ClosureChatArea:
    max_count: int = field(default=1000)
    items: list[_ChatItem] = field(default_factory=list)

    @property
    def _head(self):
        return builder.HEAD(builder.STYLE((ASSETS_PATH / "css" / "main.css").open("r", encoding="utf-8").read()))

    def elem(self):
        return builder.HTML(
            self._head,
            builder.BODY(
                builder.DIV(
                    *map(lambda item: item.elem(), self.items),
                    CLASS("akn-area"),
                    style="background-color: rgb(35, 27, 20); " "padding-top: 16px; padding-bottom: 16px;",
                )
            ),
        )

    def to_html(self, *_args, **_kwargs) -> str:
        return tostring(
            self.elem(),
            encoding="unicode",
            pretty_print=True,
        )
