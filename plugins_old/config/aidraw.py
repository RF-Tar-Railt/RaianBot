from typing import Optional
from app.config import BasePluginConfig
from pydantic import Field, AnyUrl


class Config(BasePluginConfig, domain="global"):
    txt2img: Optional[AnyUrl] = Field(default=None)
    """ai 文转图作画的接口地址"""
    img2img: Optional[AnyUrl] = Field(default=None)
    """ai 图转图作画的接口地址"""


AIDrawConfig = Config
