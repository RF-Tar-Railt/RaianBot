from typing import Optional

from pydantic import AnyUrl, Field

from app.config import BasePluginConfig


class Config(BasePluginConfig, domain="global"):
    api: Optional[AnyUrl] = Field(default=None)
    """网易云API 接口"""


MusicConfig = Config
