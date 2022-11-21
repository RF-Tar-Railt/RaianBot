from pydantic import BaseModel, Field, AnyUrl
from typing import Optional


class Config(BaseModel):
    txt2img: Optional[AnyUrl] = Field(default=None)
    """ai 文转图作画的接口地址"""
    img2img: Optional[AnyUrl] = Field(default=None)
    """ai 图转图作画的接口地址"""


AIDrawConfig = Config
