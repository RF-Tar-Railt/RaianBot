import importlib
import re
import sys
from contextlib import suppress
from pathlib import Path
from typing import List, Optional, cast, Dict, TypeVar, Type, Literal, ClassVar

import yaml
from graia.ariadne.message.element import At, Face
from loguru import logger
from pydantic import BaseModel, Field

from .context import MainConfigInstance

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

class MiraiConfig(BaseConfig):
    host: str = Field(default="localhost")
    """mirai-api-http 的链接"""

    port: int = Field(default=8080)
    """mirai-api-http 的端口"""

    verify_key: str
    """mirai-api-http 的验证码"""


class APIConfig(BaseConfig):
    host: str = Field(default="localhost")
    """FastAPI 服务的运行地址"""

    port: int = Field(default=8000)
    """FastAPI 服务的运行端口"""


class AdminConfig(BaseConfig):
    master_id: int
    """bot 的控制者的账号"""

    master_name: str
    """bot 的控制者的名字"""

    admins: List[int] = Field(default_factory=list)
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

    @property
    def headers(self):
        res = []
        for p in self.prefix:
            if mth := re.match(r"^At:(?P<target>\d+)$", p):
                res.append(At(int(mth.groupdict()["target"])))
            elif mth := re.match(r"^Face:(?P<target>.+)$", p):
                res.append(Face(name=mth.groupdict()["target"]))
            else:
                res.append(p)
        return res


class PluginConfig(BaseConfig):
    root: str = Field(default="plugins", exclude={"bots", "data", "config"})
    """模块缓存的根路径"""

    paths: List[str] = Field(default_factory=lambda x: ["plugins"])
    """模块存放的路径"""

    disabled: List[str] = Field(default_factory=list)
    """全局初始禁用的模块名称"""

    data: Dict[Type[BasePluginConfig], BasePluginConfig] = Field(default_factory=dict)
    """插件配置存放处"""

    def get(self, mtype: Type[TConfig]) -> TConfig:
        return self.data[mtype]


class PlatformConfig(BaseConfig):
    tencentcloud_secret_id: Optional[str] = Field(default=None)
    """腾讯云API 的 secret-id"""

    tencentcloud_secret_key: Optional[str] = Field(default=None)
    """腾讯云API 的 secret-key"""

    tencentcloud_tbp_bot_id: Optional[str] = Field(default=None)
    """腾讯云API 下 腾讯对话平台 (TBP) 的 bot-id"""

    tencentcloud_tbp_bot_env: Optional[Literal["dev", "release"]] = Field(default=None)
    """腾讯云API 下 腾讯对话平台 (TBP) 的 bot-env"""


class BotConfig(BaseConfig):
    bot_name: str
    """机器人名字, 请尽量不要与 prefix 重合"""

    account: int
    """bot 登录账号"""

    disabled: List[str] = Field(default_factory=list)
    """bot 初始禁用的模块名称"""

    admin: AdminConfig
    """bot 权限相关配置"""


class RaianConfig(BaseConfig):
    default_account: int
    """bot 默认登录账号"""

    cache_dir: str = Field(default="cache")
    """缓存数据存放的文件夹, 默认为 cache"""

    mirai: MiraiConfig
    """mirai-api-http 相关配置"""

    browser: BrowserConfig
    """浏览器相关配置"""

    command: CommandConfig
    """bot 命令相关配置"""

    plugin: PluginConfig
    """bot 模块相关配置"""

    api: APIConfig
    """对外接口相关配置"""

    platform: PlatformConfig
    """外部平台接口相关配置"""

    bots: Dict[int, BotConfig] = Field(default_factory=dict)
    """bot 配置"""

    root: str = Field(default="config")
    """根目录"""

    @property
    def mirai_addr(self) -> str:
        return f"http://{self.mirai.host}:{self.mirai.port}"

    @property
    def plugin_cache_dir(self) -> Path:
        return Path.cwd() / self.cache_dir / self.plugin.root

def load_config(root_dir: str = "config") -> RaianConfig:
    if (path := Path.cwd() / root_dir).exists() and path.is_dir():
        config_path = path / "config.yml"
        if config_path.exists() and config_path.is_file():
            with open(config_path, "r", encoding="utf-8") as f:
                main_config = RaianConfig.parse_obj(yaml.safe_load(f))
            main_config.root = root_dir
            configs = {}
            for config_file in (path / "bots").iterdir():
                name = config_file.name
                if name == "config.yml":
                    continue
                if name == "{example_account}.yml" or config_file.is_dir() or not config_file.stem.isdigit():
                    logger.warning(f"请将 {root_dir}/bots/{name} 重命名为你的机器人账号")
                    continue
                with config_file.open(encoding="utf-8") as f:
                    _bot_config = BotConfig.parse_obj(yaml.safe_load(f))
                    if _bot_config.account != int(config_file.stem):
                        logger.warning(f"请将 {root_dir}/bots/{name} 重命名为你的机器人账号")
                        continue
                    configs[_bot_config.account] = _bot_config
            if configs and main_config.default_account in configs:
                main_config.bots.update(configs)
                MainConfigInstance.set(main_config)
                return main_config

    logger.critical("没有有效的配置文件！")
    sys.exit()


def extract_plugin_config(plugin_path: str, name: str) -> Optional[BasePluginConfig]:
    with suppress(ModuleNotFoundError, FileNotFoundError, AttributeError, KeyError):
        config_module = importlib.import_module(f"{plugin_path}.config.{name}")
        if (base := MainConfigInstance.get(None)) and (
            path := Path.cwd() / base.root / "plugins" / f"{name}.yml"
        ).exists():
            with path.open("r+", encoding="UTF-8") as f_obj:
                data = yaml.safe_load(f_obj.read())
            return cast(BasePluginConfig, config_module.Config).parse_obj(data)
    return
