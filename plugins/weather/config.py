from typing import Optional

from app.config import BasePluginConfig
from library.heweather.data import QWeatherConfig


class Config(BasePluginConfig):
    heweather: Optional[QWeatherConfig] = None
    """是否使用和风天气的服务"""


WeatherConfig = Config
