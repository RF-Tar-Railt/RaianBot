from app.config import BasePluginConfig
from pydantic import Field


class Config(BasePluginConfig):
    heweather: bool = Field(default=True)
    """是否使用和风天气的服务"""


WeatherConfig = Config
