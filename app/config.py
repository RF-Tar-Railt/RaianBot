import importlib
import re
import sys
from contextlib import suppress
from pathlib import Path
from typing import List, Optional, cast, Dict, TypeVar, Type

import yaml
from graia.ariadne.message.element import At, Face
from loguru import logger
from pydantic import BaseModel, Field

from .context import ConfigInstance

TModel = TypeVar("TModel", bound=BaseModel)


class MiraiConfig(BaseModel):
    account: int
    """bot 登录账号"""

    host: str = Field(default="localhost")
    """mirai-api-http 的链接"""

    port: int = Field(default=8080)
    """mirai-api-http 的端口"""

    verify_key: str
    """mirai-api-http 的验证码"""


class APIConfig(BaseModel):
    host: str = Field(default="localhost")
    """FastAPI 服务的运行地址"""

    port: int = Field(default=8000)
    """FastAPI 服务的运行端口"""


class AdminConfig(BaseModel):
    master_id: int
    """bot 的控制者的账号"""

    master_name: str
    """bot 的控制者的名字"""

    admins: List[int] = Field(default_factory=list)
    """bot 的管理者(除开控制者)的账号"""


class CommandConfig(BaseModel):
    prefix: List[str] = Field(default_factory=lambda x: ["."])
    """命令前缀; At:123456 会转换为 At(123456), Face:xxx 会转换为 Face(name=xxx)"""

    help: List[str] = Field(default_factory=lambda x: ["-h", "--help"])
    """帮助选项的名称"""

    shortcut: List[str] = Field(default_factory=lambda x: ["-sct", "--shortcut"])
    """快捷命令选项的名称"""

    completion: List[str] = Field(default_factory=lambda x: ["-cp", "--comp"])
    """补全选项的名称"""


class PluginConfig(BaseModel):
    root: str = Field(default="plugins")
    """模块配置文件的根路径"""

    paths: List[str] = Field(default_factory=lambda x: ["plugins"])
    """模块存放的路径"""

    disabled: List[str] = Field(default_factory=list)
    """全局初始禁用的模块名称"""

    data: Dict[Type[BaseModel], BaseModel] = Field(default_factory=dict)
    """插件配置存放处"""

    def get(self, mtype: Type[TModel]) -> TModel:
        return self.data[mtype]


class TencentCloudAPIConfig(BaseModel):
    secret_id: str = Field(default="xxxxxxxxxxxxxxxxxxxx")
    """腾讯云API 的 secret-id"""

    secret_key: str = Field(default="xxxxxxxxxxxxxxxxxxxx")
    """腾讯云API 的 secret-key"""


class BotConfig(BaseModel):
    bot_name: str
    """机器人名字, 请尽量不要与 prefix 重合"""

    cache_dir: str = Field(default="cache")
    """缓存数据存放的文件夹, 默认为 cache"""

    mirai: MiraiConfig
    """mirai-api-http 相关配置"""

    admin: AdminConfig
    """bot 权限相关配置"""

    command: CommandConfig
    """bot 命令相关配置"""

    plugin: PluginConfig
    """bot 模块相关配置"""

    api: APIConfig
    """bot 对外接口相关配置"""

    tencent: TencentCloudAPIConfig
    """腾讯云相关配置"""

    @property
    def qq(self) -> int:
        return self.mirai.account

    @property
    def url(self) -> str:
        return f"http://{self.mirai.host}:{self.mirai.port}"

    @property
    def command_prefix(self):
        res = []
        for p in self.command.prefix:
            if mth := re.match(r"^At:(?P<target>\d+)$", p):
                res.append(At(int(mth.groupdict()["target"])))
            elif mth := re.match(r"^Face:(?P<target>.+)$", p):
                res.append(Face(name=mth.groupdict()["target"]))
            else:
                res.append(p)
        return res


def load_config(file: str = "bot_config.yml") -> BotConfig:
    if (path := Path.cwd() / "config" / file).exists():
        with path.open("r+", encoding="UTF-8") as f_obj:
            _config_data = yaml.safe_load(f_obj.read())
        cfg = BotConfig.parse_obj(_config_data)
        ConfigInstance.set(cfg)
        return cfg
    else:
        logger.critical("没有有效的配置文件！")
        sys.exit()


def extract_plugin_config(plugin_path: str, name: str) -> Optional[BaseModel]:
    with suppress(ModuleNotFoundError, FileNotFoundError, AttributeError):
        config_module = importlib.import_module(f"{plugin_path}.config.{name}")
        if (base_config := ConfigInstance.get(None)) and (
            path := Path.cwd() / "config" / base_config.plugin.root / f"{name}.yml"
        ).exists():
            with path.open("r+", encoding="UTF-8") as f_obj:
                data = yaml.safe_load(f_obj.read())
            return cast(BaseModel, config_module.Config).parse_obj(data)
    return
