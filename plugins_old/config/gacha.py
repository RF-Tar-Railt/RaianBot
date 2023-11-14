from app.config import BasePluginConfig
from pydantic import Field


class Config(BasePluginConfig, domain="global"):
    cooldown: float = Field(default=1.5)
    """抽卡的冷却时间"""


GachaConfig = Config
