from typing import Optional
from app.config import BasePluginConfig
from pydantic import Field, AnyUrl


class Config(BasePluginConfig, domain="global"):
    api: Optional[AnyUrl] = Field(default=None)
    """网易云API 接口"""


MusicConfig = Config
