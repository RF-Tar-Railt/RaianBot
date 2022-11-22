from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    NamedTuple,
    Optional,
    Type,
    TypeVar,
    Union,
)

from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.model import Friend, Group, Member
from graia.saya import Channel
from graia.saya.factory import BufferModifier, buffer_modifier, ensure_buffer

from .context import DataInstance
from .control import require_admin, require_function
from .image import create_md

Sender = Union[Group, Friend]
Target = Union[Member, Friend]
T_Callable = TypeVar("T_Callable", bound=Callable)


def meta_export(
    *,
    group_meta: Optional[List[Type[tuple]]] = None,
    user_meta: Optional[List[Type[tuple]]] = None,
):
    return Channel.current().export(
        {"group_meta": group_meta or [], "user_meta": user_meta or []}
    )


def record(name: str, require: bool = True, disable: bool = False):
    def wrapper(func: T_Callable) -> T_Callable:
        data = DataInstance.get()
        data.record(name, disable)(func)
        if require:
            buffer = ensure_buffer(func)
            buffer.setdefault("decorators", []).append(require_function(name))
        return func

    return wrapper


def permission(level: Literal["admin", "master"] = "admin"):
    def wrapper(func: T_Callable) -> T_Callable:
        buffer = ensure_buffer(func)
        buffer.setdefault("decorators", []).append(require_admin(level == "master", __record=func))
        return func
    return wrapper


async def send_handler(output: str):
    length = (output.count("\n") + 5) * 16
    if not output.startswith("#"):
        output = f"# {output}"
        output = (
            output.replace("\n\n", "\n")
            .replace("\n", "\n\n")
            .replace("#", "##")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    return MessageChain(Image(data_bytes=await create_md(output, height=length)))
