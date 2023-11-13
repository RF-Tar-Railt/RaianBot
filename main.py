from graia.scheduler.service import SchedulerService
from launart import Launart
from creart import it
from loguru import logger
import asyncio
from app.config import load_config
from app.core import RaianBotService, RaianBotDispatcher
from app.logger import setup_logger, loguru_exc_callback_async
from app.client import AiohttpClientService
from graia.saya import Saya
from graia.broadcast import Broadcast
from graia.scheduler import GraiaScheduler
from arclet.alconna import namespace
from arclet.alconna.tools import MarkdownTextFormatter
from arclet.alconna.graia import AlconnaBehaviour, AlconnaGraiaService, AlconnaDispatcher
from arclet.alconna.avilla import AlconnaAvillaAdapter
from avilla.core import Avilla
from fastapi import FastAPI
from graiax.fastapi import FastAPIBehaviour, FastAPIService
from graia.amnesia.builtins.asgi import UvicornASGIService
from graiax.playwright import PlaywrightService

from app.shortcut import send_handler

config = load_config(root_dir="my_config")
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
manager.add_component(AlconnaGraiaService(AlconnaAvillaAdapter, enable_cache=True, cache_dir=config.cache_dir))
manager.add_component(FastAPIService(fastapi))
manager.add_component(UvicornASGIService(config.api.host, config.api.port))
manager.add_component(SchedulerService(it(GraiaScheduler)))
manager.add_component(bot_service := RaianBotService(config))
bcc.finale_dispatchers.append(RaianBotDispatcher(bot_service))

AlconnaDispatcher.default_send_handler = send_handler

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

logger.success("------------------机器人初始化完毕--------------------")
avilla.launch()
logger.success("机器人关闭成功. 晚安")
