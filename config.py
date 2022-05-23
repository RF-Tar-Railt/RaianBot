import yaml
import re
import sys
from typing import List, Dict, Union, Any
from pydantic import Field, BaseModel
from loguru import logger
from pathlib import Path
from graia.ariadne.message.element import At, Face


class BotConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=8080)
    account: int
    verify_key: str
    master_id: int
    master_name: str
    prefix: List[str]
    plugin: Dict[str, Union[str, Any]]
    plugin_path: str
    disabled_plugins: List[str]
    group_meta: List[str] = Field(default_factory=list)
    user_meta: List[str] = Field(default_factory=list)

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def command_prefix(self):
        res = []
        for p in self.prefix:
            if mth := re.match(r"^At:(?P<target>\d+)$", p):
                res.append(At(int(mth.groupdict()['target'])))
            elif mth := re.match(r"^Face:(?P<target>.+)$", p):
                res.append(Face(name=mth.groupdict()['target']))
            else:
                res.append(p)
        return res


# path = Path('./my_config.yml')
path = Path('./bot_config.yml')
if path.exists():
    with path.open('r+', encoding='UTF-8') as f_obj:
        _config_data = yaml.safe_load(f_obj.read())
        bot_config: BotConfig = BotConfig.parse_obj(_config_data)
else:
    logger.critical('没有有效的配置文件！')
    sys.exit()
