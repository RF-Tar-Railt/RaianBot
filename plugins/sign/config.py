from app.config import BasePluginConfig
from pydantic import Field


class Config(BasePluginConfig):
    max: int = Field(default=200)
    """信赖最大值"""


SignConfig = Config
