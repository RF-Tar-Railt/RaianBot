from __future__ import annotations

import traceback
from contextlib import suppress
from types import TracebackType
from typing import Literal

from arclet.alconna import namespace
from arclet.alconna.graia import AlconnaBehaviour, AlconnaDispatcher, AlconnaGraiaService
from arclet.alconna.ariadne import AlconnaAriadneAdapter
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
from pathlib import Path
from arknights_toolkit import initialize

from .config import BotConfig, extract_plugin_config, RaianConfig, load_config, BasePluginConfig
from .context import BotInstance, DataInstance, MainConfigInstance, AccountDataInstance, BotConfigInstance
from .data import BotDataManager
from .logger import set_output
from .utils import send_handler

AlconnaDispatcher.default_send_handler = send_handler


class RaianBotInterface(ExportInterface["RaianBotService"]):
    service: "RaianBotService"
    def __init__(self, service: "RaianBotService", account: int | None = None):
        self.service = service
        self.account = account or Ariadne.current().account

    def bind(self, account: int):
        return RaianBotInterface(self.service, account)

    @property
    def data(self) -> BotDataManager:
        if self.account is None:
            return AccountDataInstance.get()
        return DataInstance.get()[self.account]

    @property
    def base_config(self) -> RaianConfig:
        return self.service.config

    @property
    def config(self) -> BotConfig:
        if self.account is None:
            return BotConfigInstance.get()
        return self.service.config.bots[self.account]


class RaianBotService(Service):
    id = "raian.core.service"
    supported_interface_types = {RaianBotInterface}
    config: RaianConfig

    def __init__(self, config: RaianConfig):
        super().__init__()
        self.config = config
        BotInstance.set(self)
        DataInstance.set(
            {account: BotDataManager(bot_config) for account, bot_config in config.bots.items()}
        )

    def get_interface(self, _: type[RaianBotInterface]) -> RaianBotInterface:
        return RaianBotInterface(self)

    @property
    def required(self) -> set[str | type[ExportInterface]]:
        return set()

    @property
    def stages(self) -> set[Literal["preparing", "blocking", "cleanup"]]:
        return {"preparing", "cleanup"}

    @classmethod
    def current(cls):
        """获取当前上下文的 Bot"""
        return BotInstance.get()

    async def launch(self, manager: Launart):
        datas = DataInstance.get()
        async with self.stage("preparing"):
            for account, data in datas.items():
                data.load()
                logger.debug(f"账号 {account} 数据加载完毕")
            logger.success("机器人数据加载完毕")
            saya = it(Saya)
            with saya.module_context():
                for module_info in pkgutil.iter_modules(self.config.plugin.paths):
                    path = Path(module_info.module_finder.path).stem  # noqa
                    name = module_info.name
                    if name == "config" or name.startswith("_") or f"{path}.{name}" in self.config.plugin.disabled:
                        continue
                    try:
                        if model := extract_plugin_config(path, name):
                            self.config.plugin.data[type(model)] = model
                        export_meta = saya.require(f"{path}.{name}")
                        if isinstance(export_meta, dict):
                            for data in datas.values():
                                data.add_meta(**export_meta)
                    except BaseException as e:
                        logger.warning(
                            f"fail to load {path}.{name}, caused by "
                            f"{traceback.format_exception(BaseException, e, e.__traceback__, 1)[-1]}"
                        )
                        traceback.print_exc()
                        continue

        async with self.stage("cleanup"):
            for account, data in datas.items():
                for k in list(data.cache.keys()):
                    if k.startswith("$"):
                        del data.cache[k]
                data.save()
                data.clear()
                logger.debug(f"账号 {account} 数据保存完毕")
            logger.success("机器人数据保存完毕")


class RaianBotDispatcher(BaseDispatcher):

    def __init__(self, service: RaianBotService):
        self.service = service

    async def beforeExecution(self, interface: DispatcherInterface):
        interface.local_storage["$raian_bot_config_token"] = BotConfigInstance.set(
            self.service.config.bots[Ariadne.current().account]
        )
        interface.local_storage["$raian_bot_data_token"] = AccountDataInstance.set(
            DataInstance.get()[Ariadne.current().account]
        )
    async def catch(self, interface: DispatcherInterface):
        if isinstance(interface.annotation, type):
            if interface.annotation is RaianConfig:
                return MainConfigInstance.get()
            if interface.annotation is BotConfig:
                return BotConfigInstance.get()
            if interface.annotation is BotDataManager:
                return AccountDataInstance.get()
            if issubclass(interface.annotation, BasePluginConfig):
                return self.service.config.plugin.get(interface.annotation)

    async def afterDispatch(
        self,
        interface: DispatcherInterface,
        exception: Exception | None,
        tb: TracebackType | None,
    ):
        with suppress(KeyError, RuntimeError):
            AccountDataInstance.reset(interface.local_storage["$raian_bot_data_token"])
            BotConfigInstance.reset(interface.local_storage["$raian_bot_config_token"])

def launch(debug_log: bool = True):
    """启动机器人"""
    if not (config := MainConfigInstance.get(None)):
        config = load_config()
    with namespace("Alconna") as np:
        np.headers = config.command.headers
        np.builtin_option_name["help"] = set(config.command.help)
        np.builtin_option_name["shortcut"] = set(config.command.shortcut)
        np.builtin_option_name["completion"] = set(config.command.completion)
        np.formatter_type = MarkdownTextFormatter

    saya = it(Saya)
    bcc = it(Broadcast)
    manager = Launart()
    it(AlconnaBehaviour)
    it(GraiaScheduler)
    fastapi = FastAPI()
    saya.install_behaviours(FastAPIBehaviour(fastapi))
    manager.add_service(
        PlaywrightService(
            config.browser.type,
            headless=True,
            channel=config.browser.channel,
            auto_download_browser=(not config.browser.channel),
            # user_data_dir=Path(config.cache_dir) / "browser"
        )
    )
    manager.add_service(AlconnaGraiaService(AlconnaAriadneAdapter, enable_cache=True, cache_dir=config.cache_dir))
    manager.add_service(FastAPIService(fastapi))
    manager.add_service(UvicornService(config.api.host, config.api.port))
    manager.add_service(bot_service := RaianBotService(config))
    bcc.prelude_dispatchers.append(RaianBotDispatcher(bot_service))
    Ariadne.config(launch_manager=manager, default_account=config.default_account)
    set_output("DEBUG" if debug_log else "INFO")
    for account in config.bots:
        Ariadne(
            connection=conn_cfg(
                account,
                config.mirai.verify_key,
                HttpClientConfig(config.mirai_addr),
                WebsocketClientConfig(config.mirai_addr),
            )
        )
    try:
        initialize()
    except Exception as e:
        logger.error(f"方舟资源初始化失败：{e}")
    logger.success("------------------机器人初始化完毕--------------------")
    try:
        Ariadne.launch_blocking()
    finally:
        Ariadne.stop()
        logger.success("机器人关闭成功. 晚安")


__all__ = ["RaianBotService", "send_handler", "launch", "RaianBotInterface"]
