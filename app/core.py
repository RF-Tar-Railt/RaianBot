from __future__ import annotations

import traceback
from typing import Literal

from arknights_toolkit.update.main import fetch
from creart import it
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.saya import Saya
from launart import Service, Launart
from loguru import logger
import pkgutil
from pathlib import Path

from .config import extract_plugin_config, RaianConfig, BasePluginConfig
from .context import BotInstance, DataInstance, AccountDataInstance
from .data import BotDataManager


class RaianBotService(Service):
    id = "raian.core.service"
    config: RaianConfig

    def __init__(self, config: RaianConfig):
        super().__init__()
        self.config = config
        BotInstance.set(self)
        DataInstance.set(
            {bot_config.account: BotDataManager(bot_config) for bot_config in config.bots}
        )

    @property
    def required(self) -> set[str]:
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
            if not await fetch(proxy=self.config.proxy):
                logger.error("方舟数据获取失败")
                manager.status.exiting = True
                return
            saya = it(Saya)
            with saya.module_context():
                for module_info in pkgutil.iter_modules(self.config.plugin.paths):
                    path = Path(module_info.module_finder.path).stem  # noqa
                    name = module_info.name
                    if name == "config" or name.startswith("_") or f"{path}.{name}" in self.config.plugin.disabled:
                        continue
                    try:
                        if model := extract_plugin_config(self.config, path, name):
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

    # async def beforeExecution(self, interface: DispatcherInterface):
    #     interface.local_storage["$raian_bot_config_token"] = BotConfigInstance.set(
    #         self.service.config.bots[Ariadne.current().account]
    #     )
    #     interface.local_storage["$raian_bot_data_token"] = AccountDataInstance.set(
    #         DataInstance.get()[Ariadne.current().account]
    #     )
    async def catch(self, interface: DispatcherInterface):
        if isinstance(interface.annotation, type):
            if interface.annotation is RaianConfig:
                return self.service.config
            # if interface.annotation is BotConfig:
            #     return BotConfigInstance.get()
            if interface.annotation is BotDataManager:
                return AccountDataInstance.get()
            if issubclass(interface.annotation, BasePluginConfig):
                return self.service.config.plugin.get(interface.annotation)

    # async def afterDispatch(
    #     self,
    #     interface: DispatcherInterface,
    #     exception: Exception | None,
    #     tb: TracebackType | None,
    # ):
    #     with suppress(KeyError, RuntimeError):
    #         AccountDataInstance.reset(interface.local_storage["$raian_bot_data_token"])
    #         BotConfigInstance.reset(interface.local_storage["$raian_bot_config_token"])
