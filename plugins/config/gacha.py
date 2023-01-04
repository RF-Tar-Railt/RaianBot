from app.config import BasePluginConfig
from pydantic import Field


class Config(BasePluginConfig, domain="global"):
    file: str = Field(default="assets/data/gacha_arknights.json")
    """卡池的文件路径"""
    cooldown: float = Field(default=1.5)
    """抽卡的冷却时间"""


GachaConfig = Config
