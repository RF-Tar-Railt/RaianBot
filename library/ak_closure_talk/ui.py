from __future__ import annotations

import re
from typing import List, TypeVar

from lxml.builder import E

HYPERLINK_PATTERN = re.compile(r"https?://\S+")
_T = TypeVar("_T")


def wrap_text(text: str | list, newline: bool = True, hyperlink: bool = True) -> list:
    wrapped = [text] if isinstance(text, str) else text
    if hyperlink:
        wrapped = _add_hyperlink(wrapped)
    if newline:
        wrapped = _newline_to_br(wrapped)
    return wrapped


def _newline_to_br(text: List[_T]) -> List[_T]:
    wrapped = []
    for part in text:
        if not isinstance(part, str):
            wrapped.append(part)
            continue
        lines = []
        for line in part.splitlines():
            lines.extend((E.br(), line))
        wrapped.extend(lines[1:])
    return wrapped


def _add_hyperlink(text: List[_T]) -> List[_T]:
    wrapped = []
    for part in text:
        if not isinstance(part, str):
            wrapped.append(part)
            continue
        if not (urls := HYPERLINK_PATTERN.findall(part)):
            wrapped.append(part)
            continue
        urls = [E.a(link, href=link) for link in urls]
        parts = re.split(HYPERLINK_PATTERN, part)
        for _part, url in zip(parts, urls):
            wrapped.extend((_part, url))
        wrapped.append(parts[-1])
    return wrapped
