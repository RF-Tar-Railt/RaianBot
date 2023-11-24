import inspect
from datetime import datetime
from secrets import token_hex

from arclet.alconna import Alconna
from arclet.alconna.graia import alcommand
from avilla.core import ActionFailed, BaseAccount, Context, Picture, RawResource
from avilla.standard.core.account import AccountRegistered, AccountUnregistered
from graia.saya.builtins.broadcast.shortcut import listen
from jinja2 import Environment
from jinja2.meta import find_undeclared_variables

from app.core import RaianBotService
from app.image import text2img
from app.shortcut import accessable, picture

from .config import StatusConfig
from .data import (
    CURRENT_TIMEZONE,
    get_cpu_count,
    get_cpu_status,
    get_disk_usage,
    get_memory_status,
    get_pid,
    get_python_version,
    get_swap_status,
    get_system_version,
    get_uptime,
    per_cpu_status,
)
from .helpers import humanize_date, humanize_delta, relative_time

cmd = Alconna("status")


# bot status
_run_time: datetime = datetime.now(CURRENT_TIMEZONE)
_connect_time: dict[str, datetime] = {}


@listen(AccountRegistered)
async def _(account: BaseAccount):
    _connect_time[str(account.route)] = datetime.now(CURRENT_TIMEZONE)


@listen(AccountUnregistered)
async def _(account: BaseAccount):
    _connect_time.pop(str(account.route), None)


def get_run_time() -> datetime:
    """Get the time when NoneBot started running."""
    return _run_time


def get_connect_time() -> dict[str, datetime]:
    """Get the time when the bot connected to the server."""
    return _connect_time


bot = RaianBotService.current()
config = bot.config.plugin.get(StatusConfig)


_ev = Environment(trim_blocks=True, lstrip_blocks=True, autoescape=True, enable_async=True)
_ev.globals["relative_time"] = relative_time
_ev.filters["relative_time"] = relative_time
_ev.filters["humanize_date"] = humanize_date
_ev.globals["humanize_date"] = humanize_date
_ev.filters["humanize_delta"] = humanize_delta
_ev.globals["humanize_delta"] = humanize_delta

_t_ast = _ev.parse(config.template)
_t_vars = find_undeclared_variables(_t_ast)
_t = _ev.from_string(_t_ast)

KNOWN_VARS = {
    "cpu_count": get_cpu_count,
    "cpu_usage": get_cpu_status,
    "per_cpu_usage": per_cpu_status,
    "memory_usage": get_memory_status,
    "swap_usage": get_swap_status,
    "disk_usage": get_disk_usage,
    "uptime": get_uptime,
    "runtime": get_run_time,
    "connect_time": get_connect_time,
    "python_version": get_python_version,
    "system_version": get_system_version,
    "pid": get_pid,
}


async def _solve_required_vars() -> dict:
    """Solve required variables for template rendering."""
    return (
        {k: await v() if inspect.iscoroutinefunction(v) else v() for k, v in KNOWN_VARS.items() if k in _t_vars}
        if config.truncate
        else {k: await v() if inspect.iscoroutinefunction(v) else v() for k, v in KNOWN_VARS.items()}
    )


async def render_template() -> str:
    """Render status template with required variables."""
    message = await _t.render_async(**(await _solve_required_vars()))
    return message.strip("\n")


@alcommand(cmd, post=True, send_error=True)
@accessable
async def status(ctx: Context):
    text = await render_template()
    data = await text2img(text)
    try:
        return await ctx.scene.send_message(Picture(RawResource(data)))
    except Exception:
        url = await bot.upload_to_cos(data, f"rand_op_{token_hex(16)}.png")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            return await ctx.scene.send_message(text)
