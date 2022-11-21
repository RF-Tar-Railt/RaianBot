from pydantic import BaseModel, Field


class Config(BaseModel):
    file: str = Field(default="assets/data/gacha_arknights.json")
    """卡池的文件路径"""
    cooldown: float = Field(default=1.5)
    """抽卡的冷却时间"""


GachaConfig = Config
