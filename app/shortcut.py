from __future__ import annotations

from typing import (
    Callable,
    Literal,
    TypeVar,
    Union,
)
import inspect
from pathlib import Path
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.model import Friend, Group, Member
from graia.saya import Channel
from graia.saya.factory import ensure_buffer

from .context import DataInstance
from .control import require_admin, require_function, check_disabled, check_exclusive
from .image import render_markdown

Sender = Union[Group, Friend]
Target = Union[Member, Friend]
T_Callable = TypeVar("T_Callable", bound=Callable)


def meta_export(
    *,
    group_meta: list[type[tuple]] | None = None,
    user_meta: list[type[tuple]] | None = None,
):
    return Channel.current().export(
        {"group_meta": group_meta or [], "user_meta": user_meta or []}
    )


def record(name: str, require: bool = True, disable: bool = False):
    def wrapper(func: T_Callable) -> T_Callable:
        datas = DataInstance.get()
        for data in datas.values():
            data.record(name, disable)(func)
        if require:
            buffer = ensure_buffer(func)
            buffer.setdefault("decorators", []).append(require_function(name))
        return func

    return wrapper

def accessable(path: str | T_Callable | None = None):
    def wrapper(func: T_Callable) -> T_Callable:
        nonlocal path
        buffer = ensure_buffer(func)
        if not path:
            file = inspect.getsourcefile(func)
            _path = Path(file)
            path = f"{_path.parts[-2]}.{_path.stem}"
        buffer.setdefault("decorators", []).append(check_disabled(path))
        return func

    def _wrapper(func: T_Callable) -> T_Callable:
        buffer = ensure_buffer(func)
        file = inspect.getsourcefile(func)
        _path = Path(file)
        p = f"{_path.parts[-2]}.{_path.stem}"
        buffer.setdefault("decorators", []).append(check_disabled(p))
        return func

    return _wrapper(path) if callable(path) else wrapper


def permission(level: Literal["admin", "master"] = "admin"):
    def wrapper(func: T_Callable) -> T_Callable:
        buffer = ensure_buffer(func)
        buffer.setdefault("decorators", []).append(require_admin(level == "master", __record=func))
        return func
    return wrapper


def exclusive(func: T_Callable) -> T_Callable:
    buffer = ensure_buffer(func)
    buffer.setdefault("decorators", []).append(check_exclusive())
    return func


async def send_handler(t: str, output: str):
    # length = (output.count("\n") + 5) * 16
    if t == "shortcut":
        return MessageChain(output)
    if t == "completion":
        output = (
            output.replace("\n\n", "\n")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&#123;", "{")
            .replace("&#125;", "}")
        )
        return MessageChain(output)
    if not output.startswith("#"):
        output = f"# {output}"
        output = (
            output.replace("\n\n", "\n")
            .replace("\n", "\n\n")
            .replace("#", "##")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    return MessageChain(Image(data_bytes=await render_markdown(output)))
