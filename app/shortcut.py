from __future__ import annotations

from typing import Callable, Literal, TypeVar
import inspect
from pathlib import Path
from avilla.core import Context
from avilla.core.message import MessageChain
from avilla.core.elements import Picture, Text
from avilla.core.resource import RawResource
from avilla.qqapi.resource import QQAPIImageResource
from avilla.qqapi.account import QQAPIAccount
from avilla.elizabeth.resource import ElizabethImageResource
from graia.saya.factory import ensure_buffer

from .core import RaianBotService
from .control import require_admin, require_function, check_disabled, check_exclusive
from .image import md2img

T_Callable = TypeVar("T_Callable", bound=Callable)


def picture(url: str, ctx: Context):
    if isinstance(ctx.account, QQAPIAccount):

        return Picture(QQAPIImageResource(ctx.scene.image(url), "image", url))
    return Picture(ElizabethImageResource(ctx.scene.image(url), id="", url=url))


def record(name: str, require: bool = True, disable: bool = False):
    def wrapper(func: T_Callable) -> T_Callable:
        service = RaianBotService.current()
        service.record(name, disable)(func)
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
        return MessageChain([Text(output)])
    if t == "completion":
        output = (
            output.replace("\n\n", "\n")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&#123;", "{")
            .replace("&#125;", "}")
        )
        return MessageChain([Text(output)])
    if not output.startswith("#"):
        output = f"# {output}"
        output = (
            output.replace("\n\n", "\n")
            .replace("\n", "\n\n")
            .replace("#", "##")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    return MessageChain([Picture(RawResource(await md2img(output)))])