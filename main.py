import asyncio
from secrets import token_hex

from arclet.alconna import namespace
from arclet.alconna.avilla import AlconnaAvillaAdapter
from arclet.alconna.graia import AlconnaBehaviour, AlconnaGraiaService, AlconnaOutputMessage
from arclet.alconna.tools import MarkdownTextFormatter
from avilla.core import Avilla, Context, Picture, RawResource
from avilla.core.exceptions import ActionFailed
from creart import it
from fastapi import FastAPI
from graia.amnesia.builtins.asgi import UvicornASGIService
from graia.broadcast import Broadcast
from graia.saya import Saya
from graia.scheduler import GraiaScheduler
from graia.scheduler.service import SchedulerService
from graiax.fastapi import FastAPIBehaviour, FastAPIService
from graiax.playwright import PlaywrightService
from launart import Launart
from loguru import logger

from app.client import AiohttpClientService
from app.config import load_config
from app.core import RaianBotDispatcher, RaianBotService
from app.image import md2img
from app.logger import loguru_exc_callback_async, setup_logger
from app.shortcut import picture

config = load_config(root_dir="config")
setup_logger(config.log_level)

with namespace("Alconna") as np:
    np.prefixes = config.command.headers
    np.builtin_option_name["help"] = set(config.command.help)
    np.builtin_option_name["shortcut"] = set(config.command.shortcut)
    np.builtin_option_name["completion"] = set(config.command.completion)
    np.disable_builtin_options = config.command.disables
    np.formatter_type = MarkdownTextFormatter

manager = Launart()
loop = it(asyncio.AbstractEventLoop)
loop.set_exception_handler(loguru_exc_callback_async)
saya = it(Saya)
bcc = it(Broadcast)

it(AlconnaBehaviour)
it(GraiaScheduler)
fastapi = FastAPI()
saya.install_behaviours(FastAPIBehaviour(fastapi))
manager.add_component(
    PlaywrightService(
        config.browser.type,
        headless=True,
        channel=config.browser.channel,
        auto_download_browser=(not config.browser.channel),
        # user_data_dir=Path(config.cache_dir) / "browser"
    )
)
manager.add_component(AiohttpClientService())
manager.add_component(
    AlconnaGraiaService(AlconnaAvillaAdapter, enable_cache=False, cache_dir=config.data_dir, global_remove_tome=True)
)
manager.add_component(FastAPIService(fastapi))
manager.add_component(UvicornASGIService(config.api.host, config.api.port))
manager.add_component(SchedulerService(it(GraiaScheduler)))
manager.add_component(bot_service := RaianBotService(config))
bcc.finale_dispatchers.append(RaianBotDispatcher(bot_service))


avilla = Avilla(broadcast=bcc, launch_manager=manager, record_send=True, message_cache_size=0)
protocols = {}
for bot_config in config.bots:
    t, c = bot_config.export()
    protocols.setdefault(t, []).append(c)
for protocol_type, configs in protocols.items():
    protocol = protocol_type()
    for config in configs:
        protocol.configure(config)
    avilla.apply_protocols(protocol)


@avilla.listen(AlconnaOutputMessage)
async def send_handler(output: str, otype: str, ctx: Context):
    bcc.listeners[1].oplog.clear()
    # length = (output.count("\n") + 5) * 16
    if otype in ("shortcut", "error"):
        if ctx.scene.follows("::group"):
            output = f"\n{output}"
        return await ctx.scene.send_message(output)
    if otype == "completion":
        output = (
            output.replace("\n\n", "\n")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&#123;", "{")
            .replace("&#125;", "}")
        )
        if ctx.scene.follows("::group"):
            output = f"\n{output}"
        return await ctx.scene.send_message(output)
    if not output.startswith("#"):
        output = f"# {output}"
        output = (
            output.replace("\n\n", "\n")
            .replace("\n", "\n\n")
            .replace("#", "##")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    img = await md2img(output)
    try:
        return await ctx.scene.send_message(Picture(RawResource(img)))
    except Exception:
        url = await bot_service.upload_to_cos(img, f"output_{token_hex(16)}.png")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            output = (
                output.replace("&lt;", "<")
                .replace("&gt;", ">")
                .replace("\n\n", "\n")
                .replace("##", "#")
                .replace("**", "")
            )
            if ctx.scene.follows("::group"):
                output = f"\n{output}"
            return await ctx.scene.send_message(output)


logger.success("------------------机器人初始化完毕--------------------")
avilla.launch()
logger.success("机器人关闭成功. 晚安")
