import importlib
import sys
from contextlib import suppress
from pathlib import Path
from typing import List, Optional, cast, Dict, TypeVar, Type, Literal, ClassVar, Set, Tuple, Union

import yaml
from avilla.core.elements import Notice
from avilla.elizabeth.protocol import ElizabethConfig as _ElizabethConfig, ElizabethProtocol
from avilla.qqapi.protocol import Intents as _Intents, QQAPIConfig as _QQAPIConfig,QQAPIProtocol
from loguru import logger
from pydantic import BaseModel, Field


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


class APIConfig(BaseConfig):
    host: str = Field(default="localhost")
    """FastAPI 服务的运行地址"""

    port: int = Field(default=8000)
    """FastAPI 服务的运行端口"""


class AdminConfig(BaseConfig):
    master_id: str
    """bot 的控制者的账号"""

    admins: List[str] = Field(default_factory=list)
    """bot 的管理者(除开控制者)的账号"""


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
    prefix: List[str] = Field(default_factory=lambda x: ["."])
    """命令前缀; At:123456 会转换为 At(123456), Face:xxx 会转换为 Face(name=xxx)"""

    help: List[str] = Field(default_factory=lambda x: ["-h", "--help"])
    """帮助选项的名称"""

    shortcut: List[str] = Field(default_factory=lambda x: ["-sct", "--shortcut"])
    """快捷命令选项的名称"""

    completion: List[str] = Field(default_factory=lambda x: ["-cp", "--comp"])
    """补全选项的名称"""

    disables: Set[Literal["help", "shortcut", "completion"]] = Field(default_factory=set)
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


class SqliteDatabaseConfig(BaseConfig):
    type: Literal["sqlite"] = "sqlite"
    name: str
    driver: str = "aiosqlite"

    class Config:
        extra = "allow"


class MySqlDatabaseConfig(BaseConfig):
    type: Literal["mysql"] = "mysql"
    name: str
    driver: str = "pymysql"
    host: str
    port: int = 3306
    username: str
    password: str

    class Config:
        extra = "allow"


class PluginConfig(BaseConfig):
    root: str = Field(default="plugins", exclude={"bots", "data", "config"})
    """模块各数据的根路径"""

    paths: List[str] = Field(default_factory=lambda x: ["plugins"])
    """模块存放的路径"""

    disabled: List[str] = Field(default_factory=list)
    """全局初始禁用的模块名称"""

    configs: Dict[Type[BasePluginConfig], BasePluginConfig] = Field(default_factory=dict)
    """插件配置存放处"""

    def get(self, mtype: Type[TConfig]) -> TConfig:
        return self.configs[mtype]


class PlatformConfig(BaseConfig):
    tencentcloud_secret_id: Optional[str] = Field(default=None)
    """腾讯云API 的 secret-id"""

    tencentcloud_secret_key: Optional[str] = Field(default=None)
    """腾讯云API 的 secret-key"""

    tencentcloud_tbp_bot_id: Optional[str] = Field(default=None)
    """腾讯云API 下 腾讯对话平台 (TBP) 的 bot-id"""

    tencentcloud_tbp_bot_env: Optional[Literal["dev", "release"]] = Field(default=None)
    """腾讯云API 下 腾讯对话平台 (TBP) 的 bot-env"""


class ElizabethConfig(BaseConfig):
    type: Literal["mirai"] = "mirai"

    name: str
    """机器人名字, 请尽量不要与 prefix 重合"""

    account: str
    """bot 登录账号"""

    host: str
    """mirai-api-http 的地址"""

    port: int
    """mirai-api-http 的端口"""

    access_token: str
    """mirai-api-http 的鉴权"""

    disabled: List[str] = Field(default_factory=list)
    """bot 初始禁用的模块名称"""

    admin: AdminConfig
    """bot 权限相关配置"""

    def export(self):
        return ElizabethProtocol, _ElizabethConfig(
            qq=int(self.account),
            host=self.host,
            port=self.port,
            access_token=self.access_token
        )


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


class QQAPIConfig(BaseConfig):
    type: Literal["qqapi"] = "qqapi"

    name: str
    """机器人名字, 请尽量不要与 prefix 重合"""

    account: str
    """bot 的appid"""

    token: str
    """bot 的令牌"""

    secret: str
    """bot 的密钥"""

    shard: Optional[Tuple[int, int]] = None
    """分片设置"""

    intent: Intents = Field(default_factory=Intents)
    """事件接收配置"""

    is_sandbox: bool = False
    """是否为沙箱环境"""

    disabled: List[str] = Field(default_factory=list)
    """bot 初始禁用的模块名称"""

    admin: AdminConfig
    """bot 权限相关配置"""

    def export(self):
        return QQAPIProtocol, _QQAPIConfig(
            id=self.account, token=self.token, secret=self.secret, shard=self.shard,
            intent=self.intent.export(), is_sandbox=self.is_sandbox
        )


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

    database: Union[SqliteDatabaseConfig, MySqlDatabaseConfig]
    """bot 数据库相关配置"""

    plugin: PluginConfig
    """bot 模块相关配置"""

    api: APIConfig
    """对外接口相关配置"""

    platform: PlatformConfig
    """外部平台接口相关配置"""

    bots: List[Union[ElizabethConfig, QQAPIConfig]] = Field(default_factory=list)
    """bot 配置"""

    root: str = Field(default="config")
    """根目录"""
    @property
    def plugin_data_dir(self) -> Path:
        return Path.cwd() / self.data_dir / self.plugin.root


def load_config(root_dir: str = "config") -> RaianConfig:
    if (path := Path.cwd() / root_dir).exists() and path.is_dir():
        config_path = path / "config.yml"
        if config_path.exists() and config_path.is_file():
            with open(config_path, "r", encoding="utf-8") as f:
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
