from typing import Union, Optional, List
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.util.saya import ensure_cube_as_listener, Wrapper, T_Callable, ListenerSchema, Cube
from graia.ariadne.model import Group, Friend, Member
from graia.saya import Channel
from graia.scheduler.saya import SchedulerSchema
from graia.scheduler import Timer
from arclet.alconna.graia import AlconnaDispatcher, Alconna

from .core import RaianMain
from .control import require_function

Sender = Union[Group, Friend]
Target = Union[Member, Friend]


def meta(author: Optional[List[str]] = None, name: Optional[str] = None, description: Optional[str] = None):
    channel = Channel.current()
    channel.meta['author'] = author or []
    channel.meta['name'] = name
    channel.meta['description'] = description


def command(alconna: Alconna, allow_private: bool = True) -> Wrapper:
    if '$' in alconna.help_text:
        alconna.help_text = alconna.help_text.replace('$', alconna.headers[0], 1)

    def wrapper(func: T_Callable) -> T_Callable:
        cube: Cube[ListenerSchema] = ensure_cube_as_listener(func)
        cube.metaclass.listening_events.extend([GroupMessage, FriendMessage] if allow_private else [GroupMessage])
        cube.metaclass.inline_dispatchers.append(AlconnaDispatcher(alconna, help_flag='reply'))
        return func

    return wrapper


def record(name: str, require: bool = True) -> Wrapper:
    def wrapper(func: T_Callable) -> T_Callable:
        bot = RaianMain.current()
        bot.data.record(name)(func)
        if require:
            cube: Cube[ListenerSchema] = ensure_cube_as_listener(func)
            cube.metaclass.decorators.append(require_function(name))
        return func

    return wrapper


def schedule(timer: Timer) -> Wrapper:
    def wrapper(func: T_Callable) -> T_Callable:
        channel = Channel.current()
        channel.use(SchedulerSchema(timer))(func)
        return func

    return wrapper
