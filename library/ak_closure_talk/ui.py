from __future__ import annotations

import re

from lxml.builder import E

HYPERLINK_PATTERN = re.compile(r"https?://\S+")


def wrap_text(text: str | list, newline: bool = True, hyperlink: bool = True):
    wrapped = [text] if isinstance(text, str) else text
    if hyperlink:
        wrapped = _add_hyperlink(wrapped)
    if newline:
        wrapped = _newline_to_br(wrapped)
    return wrapped


def _newline_to_br(text: list):
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


def _replace_with_hyperlink(text: str, link: str):
    wrapped = []
    for piece in text.split(link):
        wrapped.extend((piece, E.a(link, href=link)))
    return wrapped[:-1]


def _add_hyperlink(text: list):
    wrapped = []
    for part in text:
        if not isinstance(part, str):
            wrapped.append(part)
            continue
        if not (urls := HYPERLINK_PATTERN.findall(part)):
            wrapped.append(part)
            continue
        parts = []
        for url in urls:
            parts.extend(_replace_with_hyperlink(part, url))
        wrapped.extend(parts)
    return wrapped
