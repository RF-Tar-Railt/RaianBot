import pkgutil
import traceback
from contextvars import ContextVar
from pathlib import Path
from typing import Literal, Union

from arknights_toolkit.update.main import fetch
from avilla.core import Context
from creart import it
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.exceptions import PropagationCancelled
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.saya import Saya
from launart import Launart, Service
from loguru import logger

from .config import BasePluginConfig, BotConfig, RaianConfig, extract_plugin_config
from .cos import CosConfig, put_object
from .database import DatabaseService
from .statistic import Statistic, commit

BotServiceCtx: ContextVar["RaianBotService"] = ContextVar("bot_service")


class RaianBotService(Service):
    id = "raian.core.service"
    config: RaianConfig
    db: DatabaseService

    def __init__(self, config: RaianConfig):
        super().__init__()
        self.config = config
        (Path.cwd() / self.config.data_dir).mkdir(parents=True, exist_ok=True)
        self.cache = {}

    def ensure_manager(self, manager: Launart):
        super().ensure_manager(manager)
        if self.config.database.type == "sqlite":
            self.config.database.name = f"{self.config.data_dir}/{self.config.database.name}"
            if not self.config.database.name.endswith(".db"):
                self.config.database.name = f"{self.config.database.name}.db"
        manager.add_component(
            db := DatabaseService(
                self.config.database.url,
                {"echo": None, "pool_pre_ping": True},
            )
        )
        self.db = db

    @property
    def required(self) -> set[str]:
        return set()

    @property
    def stages(self) -> set[Literal["preparing", "blocking", "cleanup"]]:
        return {"preparing", "cleanup"}

    @classmethod
    def current(cls):
        """获取当前上下文的 Bot"""
        return BotServiceCtx.get()

    async def launch(self, manager: Launart):
        token = BotServiceCtx.set(self)
        async with self.stage("preparing"):
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
                            self.config.plugin.configs[type(model)] = model
                        saya.require(f"{path}.{name}.main")
                    except BaseException as e:
                        logger.warning(
                            f"fail to load {path}.{name}, caused by "
                            f"{traceback.format_exception(BaseException, e, e.__traceback__, 1)[-1]}"
                        )
                        traceback.print_exc()
                        continue
        async with self.stage("cleanup"):
            self.cache.clear()
            logger.success("机器人数据保存完毕")

        BotServiceCtx.reset(token)

    def record(self, name: str, disable: bool = False):
        def __wrapper__(func):
            record = self.cache.setdefault("function::record", {})
            disables = self.cache.setdefault("function::disables", set())
            record.setdefault(name, func)
            func.__record__ = name
            if disable:
                disables.add(name)
            return func

        return __wrapper__

    @property
    def functions(self):
        return self.cache.get("function::record", {})

    @property
    def disabled(self):
        return self.cache.get("function::disables", set())

    def func_description(self, name: str):
        return func.__doc__ if (func := self.cache.get("function::record", {}).get(name)) else "Unknown"

    async def upload_to_cos(self, content: Union[bytes, str], name: str):
        config = CosConfig(
            secret_id=self.config.platform.tencentcloud_secret_id,
            secret_key=self.config.platform.tencentcloud_secret_key,
            region=self.config.platform.tencentcloud_region,
            scheme="https",
        )
        await put_object(
            config, self.config.platform.tencentcloud_bucket, content, name, headers={"StorageClass": "STANDARD"}
        )
        return config.uri(self.config.platform.tencentcloud_bucket, name)


class RaianBotDispatcher(BaseDispatcher):
    def __init__(self, service: RaianBotService):
        self.service = service

    async def catch(self, interface: DispatcherInterface):
        if interface.annotation is RaianBotService:
            return self.service
        if interface.annotation is RaianConfig:
            return self.service.config
        if isinstance(interface.annotation, type):
            if issubclass(interface.annotation, Service):
                manager = Launart.current()
                return manager.get_component(interface.annotation)
            if issubclass(interface.annotation, BasePluginConfig):
                return self.service.config.plugin.get(interface.annotation)
            if hasattr(interface.event, "context"):
                context: Context = interface.event.context
                if issubclass(interface.annotation, BotConfig):
                    return next(
                        (bot for bot in self.service.config.bots if bot.ensure(context.account)), None  # type: ignore
                    )

    async def afterExecution(
        self,
        interface: DispatcherInterface,
        exception: Union[Exception, None],
        tb: ...,
    ):
        if interface.depth > 0 or exception:
            return
        await interface.exec_result
        result = interface.exec_result.result()
        if isinstance(result, Statistic):
            await commit(self.service.db, result)
            raise PropagationCancelled
