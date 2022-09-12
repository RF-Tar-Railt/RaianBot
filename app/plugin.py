from typing import Union, Optional, List
from graia.ariadne.util.saya import ensure_cube_as_listener, Wrapper, T_Callable, ListenerSchema, Cube
from graia.ariadne.model import Group, Friend, Member
from graia.saya import Channel
from graia.scheduler.saya import SchedulerSchema
from graia.scheduler import Timer

from .core import RaianMain
from .control import require_function, require_admin

Sender = Union[Group, Friend]
Target = Union[Member, Friend]


def meta(author: Optional[List[str]] = None, name: Optional[str] = None, description: Optional[str] = None):
    channel = Channel.current()
    channel.meta['author'] = author or []
    channel.meta['name'] = name
    channel.meta['description'] = description


def record(name: str, require: bool = True, disable: bool = False) -> Wrapper:
    def wrapper(func: T_Callable) -> T_Callable:
        bot = RaianMain.current()
        bot.data.record(name, disable)(func)
        if require:
            cube: Cube[ListenerSchema] = ensure_cube_as_listener(func)
            cube.metaclass.decorators.append(require_function(name))
        return func

    return wrapper


def admin(func: T_Callable) -> T_Callable:
    cube: Cube[ListenerSchema] = ensure_cube_as_listener(func)
    cube.metaclass.decorators.append(require_admin(False))
    return func


def master(func: T_Callable) -> T_Callable:
    cube: Cube[ListenerSchema] = ensure_cube_as_listener(func)
    cube.metaclass.decorators.append(require_admin(True))
    return func


def schedule(timer: Timer) -> Wrapper:
    def wrapper(func: T_Callable) -> T_Callable:
        channel = Channel.current()
        channel.use(SchedulerSchema(timer, True))(func)
        return func

    return wrapper
