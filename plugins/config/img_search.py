from typing import Optional
from app.config import BasePluginConfig
from pydantic import Field


class Config(BasePluginConfig):
    saucenao: Optional[str] = Field(default=None)
    """saucenao的token, 请自行前往 https://saucenao.com 中获取"""
    ascii2d: bool = Field(default=True)
    """是否使用 ascii2d"""
    iqdb: bool = Field(default=True)
    """是否使用 iqdb"""


ImgSearchConfig = Config
