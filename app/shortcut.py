from __future__ import annotations

import inspect
from pathlib import Path
from typing import Callable, Literal, TypeVar

from avilla.core import Context
from avilla.core.account import BaseAccount
from avilla.core.elements import Picture
from avilla.elizabeth.resource import ElizabethImageResource
from avilla.qqapi.account import QQAPIAccount
from avilla.qqapi.resource import QQAPIImageResource
from graia.saya.factory import ensure_buffer

from .control import check_disabled, require_account, require_admin, require_function
from .core import RaianBotService

T_Callable = TypeVar("T_Callable", bound=Callable)


def is_qqapi_group(ctx: Context):
    return isinstance(ctx.account, QQAPIAccount) and ctx.scene.follows("::group")


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


def allow(*atype: type[BaseAccount]):
    def wrapper(func: T_Callable) -> T_Callable:
        buffer = ensure_buffer(func)
        buffer.setdefault("decorators", []).append(require_account(atype))
        return func

    return wrapper


# def exclusive(func: T_Callable) -> T_Callable:
#     buffer = ensure_buffer(func)
#     buffer.setdefault("decorators", []).append(check_exclusive())
#     return func
