from typing import Optional

from app.config import BasePluginConfig


class Config(BasePluginConfig, domain="global"):
    file: Optional[str] = None
    """卡池的文件路径"""


GachaConfig = Config
