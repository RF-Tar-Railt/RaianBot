from pydantic import Field

from app.config import BasePluginConfig


class Config(BasePluginConfig):
    heweather: bool = Field(default=True)
    """是否使用和风天气的服务"""


WeatherConfig = Config
