from pydantic import BaseModel, Field
from typing import Optional


class Config(BaseModel):
    saucenao: Optional[str] = Field(default=None)
    """saucenao的token, 请自行前往 https://saucenao.com 中获取"""
    ascii2d: bool = Field(default=True)
    """是否使用 ascii2d"""
    iqdb: bool = Field(default=True)
    """是否使用 iqdb"""


ImgSearchConfig = Config
