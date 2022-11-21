from pydantic import BaseModel, Field, AnyUrl
from typing import Optional


class Config(BaseModel):
    api: Optional[AnyUrl] = Field(default=None)
    """网易云API 接口"""


MusicConfig = Config
