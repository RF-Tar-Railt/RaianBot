from graia.scheduler.service import SchedulerService
from launart import Launart
from creart import it
from loguru import logger

from app.config import load_config
from app.core import RaianBotService, RaianBotDispatcher
from app.logger import setup
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

config = load_config()
setup(config.log_level)

with namespace("Alconna") as np:
    np.prefixes = config.command.headers
    np.builtin_option_name["help"] = set(config.command.help)
    np.builtin_option_name["shortcut"] = set(config.command.shortcut)
    np.builtin_option_name["completion"] = set(config.command.completion)
    np.disable_builtin_options = config.command.disables
    np.formatter_type = MarkdownTextFormatter

manager = Launart()

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
manager.add_component(AlconnaGraiaService(AlconnaAvillaAdapter, enable_cache=True, cache_dir=config.cache_dir))
manager.add_component(FastAPIService(fastapi))
manager.add_component(UvicornASGIService(config.api.host, config.api.port))
manager.add_component(SchedulerService(it(GraiaScheduler)))
manager.add_component(bot_service := RaianBotService(config))
bcc.finale_dispatchers.append(RaianBotDispatcher(bot_service))

AlconnaDispatcher.default_send_handler = send_handler

avilla = Avilla(broadcast=bcc, launch_manager=manager, record_send=True, message_cache_size=0)
avilla.apply_protocols(*(bot.export() for bot in config.bots))

logger.success("------------------机器人初始化完毕--------------------")
avilla.launch()
logger.success("机器人关闭成功. 晚安")
