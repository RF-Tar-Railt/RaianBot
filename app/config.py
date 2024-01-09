import importlib
import sys
from contextlib import suppress
from pathlib import Path
from typing import ClassVar, Generic, Literal, Optional, TypeVar, Union, cast

import yaml
from avilla.core import Selector
from avilla.core.account import BaseAccount
from avilla.core.elements import Notice
from avilla.elizabeth.account import ElizabethAccount
from avilla.elizabeth.protocol import ElizabethConfig as _ElizabethConfig
from avilla.elizabeth.protocol import ElizabethProtocol
from avilla.qqapi.account import QQAPIAccount
from avilla.qqapi.protocol import Intents as _Intents
from avilla.qqapi.protocol import QQAPIConfig as _QQAPIConfig
from avilla.qqapi.protocol import QQAPIProtocol
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.engine.url import URL


class BaseConfig(BaseModel):
    class Config:
        extra = "ignore"


class BasePluginConfig(BaseModel):
    is_global: ClassVar[bool] = False

    @classmethod
    def __init_subclass__(cls, **kwargs):
        if kwargs.get("domain", "global") == "global":
            cls.is_global = True

    class Config:
        extra = "ignore"


TConfig = TypeVar("TConfig", bound=BasePluginConfig)
TA = TypeVar("TA", bound=BaseAccount)


class APIConfig(BaseConfig):
    host: str = Field(default="localhost")
    """FastAPI 服务的运行地址"""

    port: int = Field(default=8000)
    """FastAPI 服务的运行端口"""


class BrowserConfig(BaseConfig):
    type: Literal["chromium", "firefox", "webkit"] = Field(default="chromium")
    """Playwright 浏览器类型"""

    channel: Optional[
        Literal[
            "chrome",
            "chrome-beta",
            "chrome-dev",
            "chrome-canary",
            "msedge",
            "msedge-beta",
            "msedge-dev",
            "msedge-canary",
        ]
    ] = Field(default=None)
    """本地浏览器通道，不指定则使用下载的浏览器"""


class CommandConfig(BaseConfig):
    prefix: list[str] = Field(default_factory=lambda x: ["."])
    """命令前缀; At:123456 会转换为 At(123456), Face:xxx 会转换为 Face(name=xxx)"""

    help: list[str] = Field(default_factory=lambda x: ["-h", "--help"])
    """帮助选项的名称"""

    shortcut: list[str] = Field(default_factory=lambda x: ["-sct", "--shortcut"])
    """快捷命令选项的名称"""

    completion: list[str] = Field(default_factory=lambda x: ["-cp", "--comp"])
    """补全选项的名称"""

    disables: set[Literal["help", "shortcut", "completion"]] = Field(default_factory=set)
    """禁用内置选项"""

    @property
    def headers(self):
        res = []
        for p in self.prefix:
            if p == "$Notice":
                res.append(Notice)
            else:
                res.append(p)
        return res


class DatabaseConfig(BaseConfig):
    type: str = "sqlite"
    name: str
    driver: str = "aiosqlite"
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    query: dict[str, Union[list[str], str]] = Field(default_factory=dict)

    @property
    def url(self) -> URL:
        if self.type == "sqlite":
            return URL.create(f"{self.type}+{self.driver}", database=self.name, query=self.query)
        return URL.create(
            f"{self.type}+{self.driver}", self.username, self.password, self.host, self.port, self.name, self.query
        )


class PluginConfig(BaseConfig):
    root: str = Field(default="plugins", exclude={"bots", "data", "config"})
    """模块各数据的根路径"""

    paths: list[str] = Field(default_factory=lambda x: ["plugins"])
    """模块存放的路径"""

    disabled: list[str] = Field(default_factory=list)
    """全局初始禁用的模块名称"""

    configs: dict[type[BasePluginConfig], BasePluginConfig] = Field(default_factory=dict)
    """插件配置存放处"""

    def get(self, mtype: type[TConfig]) -> TConfig:
        return self.configs[mtype]


class PlatformConfig(BaseConfig):
    tencentcloud_region: Optional[str] = Field(default=None)
    """腾讯云API 的 region"""

    tencentcloud_secret_id: Optional[str] = Field(default=None)
    """腾讯云API 的 secret-id"""

    tencentcloud_secret_key: Optional[str] = Field(default=None)
    """腾讯云API 的 secret-key"""

    tencentcloud_tbp_bot_id: Optional[str] = Field(default=None)
    """腾讯云API 下 腾讯对话平台 (TBP) 的 bot-id"""

    tencentcloud_tbp_bot_env: Optional[Literal["dev", "release"]] = Field(default=None)
    """腾讯云API 下 腾讯对话平台 (TBP) 的 bot-env"""

    tencentcloud_bucket: Optional[str] = Field(default=None)
    """腾讯云API 下 COS 的 bucket"""

    heweather_api_key: Optional[str] = Field(default=None)
    """和风天气API 的 key

    获取地址: https://id.qweather.com/#/login
    """

    heweather_api_type: Optional[Literal[0, 1, 2]] = Field(default=None)
    """和风天气API 的类型

    0 = 普通版，免费订阅 (3 天天气预报)
    1 = 个人开发版，标准订阅 (7 天天气预报)
    2 = 商业版 (7 天天气预报)
    """

    heweather_api_hourly_type: Literal[1, 2] = Field(default=1)
    """和风天气API 的逐小时类型

    1 = 未来12小时 (默认值)
    2 = 未来24小时
    """


class BotConfig(BaseConfig, Generic[TA]):
    type: str
    """机器人类型"""

    name: str
    """机器人名字, 请尽量不要与 prefix 重合"""

    account: str
    """bot 账号"""

    master_id: str
    """bot 的控制者的账号"""

    admins: list[str] = Field(default_factory=list)
    """bot 的管理者(除开控制者)的账号"""

    def export(self):
        raise NotImplementedError

    def master(self, channel: Optional[str] = None) -> Selector:
        raise NotImplementedError

    def administrators(self, channel: Optional[str] = None) -> list[Selector]:
        raise NotImplementedError

    def ensure(self, account: TA):
        ...


class ElizabethConfig(BotConfig[ElizabethAccount]):
    type: Literal["mirai"] = "mirai"

    host: str
    """mirai-api-http 的地址"""

    port: int
    """mirai-api-http 的端口"""

    access_token: str
    """mirai-api-http 的鉴权"""

    def export(self):
        return ElizabethProtocol, _ElizabethConfig(
            qq=int(self.account), host=self.host, port=self.port, access_token=self.access_token
        )

    def master(self, channel: Optional[str] = None) -> Selector:
        if not channel:
            return Selector.from_follows_pattern(f"land(qq).friend({self.master_id})")
        return Selector.from_follows_pattern(f"land(qq).group({channel}).member({self.master_id})")

    def administrators(self, channel: Optional[str] = None) -> list[Selector]:
        if not channel:
            return [Selector.from_follows_pattern(f"land(qq).friend({admin})") for admin in self.admins]
        return [Selector.from_follows_pattern(f"land(qq).group({channel}).member({admin})") for admin in self.admins]

    def ensure(self, account: ElizabethAccount):
        return account.connection.account_id == int(self.account)


class Intents(BaseConfig):
    guilds: bool = True
    guild_members: bool = True
    guild_messages: bool = False
    """GUILD_MESSAGES"""
    guild_message_reactions: bool = True
    direct_message: bool = False
    """DIRECT_MESSAGES"""
    open_forum_event: bool = False
    audio_live_member: bool = False
    c2c_group_at_messages: bool = False
    interaction: bool = False
    message_audit: bool = True
    forum_event: bool = False
    audio_action: bool = False
    at_messages: bool = True

    def export(self):
        return _Intents(**self.dict())


class QQAPIConfig(BotConfig[QQAPIAccount]):
    type: Literal["qqapi"] = "qqapi"

    token: str
    """bot 的令牌"""

    secret: str
    """bot 的密钥"""

    shard: Optional[tuple[int, int]] = None
    """分片设置"""

    intent: Intents = Field(default_factory=Intents)
    """事件接收配置"""

    is_sandbox: bool = False
    """是否为沙箱环境"""

    def export(self):
        return QQAPIProtocol, _QQAPIConfig(
            id=self.account,
            token=self.token,
            secret=self.secret,
            shard=self.shard,
            intent=self.intent.export(),
            is_sandbox=self.is_sandbox,
        )

    def master(self, channel: Optional[str] = None) -> Selector:
        if not channel:
            return Selector.from_follows_pattern(f"land(qq).user({self.master_id})")
        return Selector.from_follows_pattern(f"land(qq).channel({channel}).member({self.master_id})")

    def administrators(self, channel: Optional[str] = None) -> list[Selector]:
        if not channel:
            return [Selector.from_follows_pattern(f"land(qq).user({admin})") for admin in self.admins]
        return [Selector.from_follows_pattern(f"land(qq).channel({channel}).member({admin})") for admin in self.admins]

    def ensure(self, account: QQAPIAccount):
        return account.connection.config.id == self.account  # type: ignore


class RaianConfig(BaseConfig):
    data_dir: str = Field(default="data")
    """数据存放的文件夹, 默认为 data"""

    log_level: str = Field(default="INFO")
    """日志等级"""

    proxy: Optional[str] = Field(default=None)
    """代理配置"""

    browser: BrowserConfig
    """浏览器相关配置"""

    command: CommandConfig
    """bot 命令相关配置"""

    database: DatabaseConfig
    """bot 数据库相关配置"""

    plugin: PluginConfig
    """bot 模块相关配置"""

    api: APIConfig
    """对外接口相关配置"""

    platform: PlatformConfig
    """外部平台接口相关配置"""

    bots: list[Union[ElizabethConfig, QQAPIConfig]] = Field(default_factory=list)
    """bot 配置"""

    root: str = Field(default="config")
    """根目录"""

    @property
    def plugin_data_dir(self) -> Path:
        return Path.cwd() / self.data_dir / self.plugin.root


def load_config(root_dir: Union[str, Path] = "config") -> RaianConfig:
    if (path := Path.cwd().joinpath(root_dir)).exists() and path.is_dir():
        config_path = path / "config.yml"
        if config_path.exists() and config_path.is_file():
            with open(config_path, encoding="utf-8") as f:
                main_config = RaianConfig.parse_obj(yaml.safe_load(f))
            main_config.root = root_dir
            for bot in main_config.bots.copy():
                if bot.account == "UNDEFINED":
                    main_config.bots.remove(bot)
            return main_config

    logger.critical("没有有效的配置文件！")
    sys.exit()


def extract_plugin_config(main_config: RaianConfig, plugin_path: str, name: str) -> Optional[BasePluginConfig]:
    with suppress(ModuleNotFoundError, FileNotFoundError, AttributeError, KeyError):
        config_module = importlib.import_module(f"{plugin_path}.{name}.config")
        if (path := Path.cwd() / main_config.root / "plugins" / f"{name}.yml").exists():
            with path.open("r+", encoding="UTF-8") as f_obj:
                data = yaml.safe_load(f_obj.read())
            return cast(BasePluginConfig, config_module.Config).parse_obj(data)
    return
