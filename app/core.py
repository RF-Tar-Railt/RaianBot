import sys
import traceback
from typing import Literal, Set, Type, Union

from arclet.alconna import Alconna, namespace
from arclet.alconna.graia import AlconnaBehaviour, AlconnaDispatcher
from arclet.alconna.tools.formatter import MarkdownTextFormatter
from creart import it
from fastapi import FastAPI
from graia.broadcast import Broadcast
from graia.amnesia.builtins.uvicorn import UvicornService
from graia.ariadne.app import Ariadne
from graia.ariadne.connection.config import HttpClientConfig, WebsocketClientConfig
from graia.ariadne.connection.config import config as conn_cfg
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.saya import Saya
from graia.scheduler import GraiaScheduler
from graiax.fastapi import FastAPIBehaviour, FastAPIService
from graiax.playwright import PlaywrightService
from launart import ExportInterface, Service, Launart
from loguru import logger
import pkgutil

from .config import BotConfig, extract_plugin_config
from .context import BotInstance, ConfigInstance, DataInstance
from .data import BotDataManager
from .logger import set_output
from .utils import send_handler

AlconnaDispatcher.default_send_handler = send_handler


class RaianBotInterface(ExportInterface):
    @property
    def data(self) -> BotDataManager:
        return DataInstance.get(None)

    @property
    def config(self) -> BotConfig:
        return ConfigInstance.get(None)


class RaianBotService(Service):
    id = "raian.core.service"
    supported_interface_types = {RaianBotInterface}
    data: BotDataManager
    config: BotConfig

    def __init__(self, config: BotConfig):
        super().__init__()
        self.config = config
        self.data = DataInstance.get(None) or BotDataManager()
        BotInstance.set(self)

    def get_interface(self, _: Type[RaianBotInterface]) -> RaianBotInterface:
        return RaianBotInterface()

    @property
    def required(self) -> Set[Union[str, Type[ExportInterface]]]:
        return set()

    @property
    def stages(self) -> Set[Literal["preparing", "blocking", "cleanup"]]:
        return {"preparing", "cleanup"}

    @classmethod
    def current(cls):
        """获取当前上下文的 Bot"""
        return BotInstance.get()

    async def launch(self, manager: Launart):
        async with self.stage("preparing"):
            try:
                self.data.load()
                logger.debug("机器人数据加载完毕")
                with it(Saya).module_context():
                    for module_info in pkgutil.iter_modules(self.config.plugin.paths):
                        path = module_info.module_finder.path  # noqa
                        name = module_info.name
                        if (
                            name == "config"
                            or name.startswith("_")
                            or f"{path}.{name}" in self.config.plugin.disabled
                        ):
                            continue
                        try:
                            if model := extract_plugin_config(path, name):
                                self.config.plugin.data[type(model)] = model
                            export_meta = it(Saya).require(f"{path}.{name}")
                            if isinstance(export_meta, dict):
                                DataInstance.get().add_meta(**export_meta)
                        except BaseException as e:
                            logger.warning(
                                f"fail to load {path.name}.{name}, caused by "
                                f"{traceback.format_exception(BaseException, e, e.__traceback__, 1)[-1]}"
                            )
                            manager.status.exiting = True
                            traceback.print_exc()
                            break
            except RuntimeError:
                manager.status.exiting = True

        async with self.stage("cleanup"):
            self.data.save()
            logger.debug("机器人数据保存完毕")


class RaianBotDispatcher(BaseDispatcher):
    async def catch(self, interface: DispatcherInterface):
        if isinstance(interface.annotation, type):
            if interface.annotation is Launart:
                return Launart.current()
            if interface.annotation is BotConfig:
                return ConfigInstance.get()
            if interface.annotation is BotDataManager:
                return DataInstance.get()
            if issubclass(interface.annotation, ExportInterface):
                return Launart.current().get_interface(interface.annotation)


def launch(debug_log: bool = True):
    """启动机器人"""
    if not (config := ConfigInstance.get(None)):
        logger.critical("请先加载配置，再初始化机器人！")
        sys.exit(1)
    with namespace("Alconna") as np:
        np.headers = config.command_prefix
        np.builtin_option_name['help'] = set(config.command.help)
        np.builtin_option_name['shortcut'] = set(config.command.shortcut)
        np.builtin_option_name['completion'] = set(config.command.completion)

    Alconna.config(formatter_type=MarkdownTextFormatter)
    saya = it(Saya)
    bcc = it(Broadcast)
    bcc.prelude_dispatchers.append(RaianBotDispatcher())
    manager = Launart()
    it(AlconnaBehaviour)
    it(GraiaScheduler)
    fastapi = FastAPI()
    saya.install_behaviours(FastAPIBehaviour(fastapi))
    manager.add_service(PlaywrightService("chromium", headless=True, auto_download_browser=False, channel="msedge"))
    manager.add_service(FastAPIService(fastapi))
    manager.add_service(UvicornService(config.api.host, config.api.port))
    manager.add_service(RaianBotService(config))
    Ariadne.config(launch_manager=manager)
    set_output("DEBUG" if debug_log else "INFO")
    Ariadne(
        connection=conn_cfg(
            config.mirai.account,
            config.mirai.verify_key,
            HttpClientConfig(config.url),
            WebsocketClientConfig(config.url),
        )
    )
    logger.success("------------------机器人初始化完毕--------------------")
    try:
        Ariadne.launch_blocking()
    finally:
        Ariadne.stop()
        logger.success("机器人关闭成功. 晚安")


__all__ = ["RaianBotService", "send_handler", "launch", "RaianBotInterface"]
