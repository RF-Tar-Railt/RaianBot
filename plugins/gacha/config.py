from app.config import BasePluginConfig
from typing import Optional


class Config(BasePluginConfig, domain="global"):
    file: Optional[str] = None
    """卡池的文件路径"""


GachaConfig = Config
