from pydantic import Field

from app.config import BasePluginConfig


class Config(BasePluginConfig):
    max: int = Field(default=200)
    """信赖最大值"""


SignConfig = Config
