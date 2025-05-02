from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Now(BaseModel):
    obsTime: str
    temp: str
    icon: str
    text: str
    windScale: str
    windDir: str
    humidity: str
    precip: str
    vis: str

    model_config = ConfigDict(extra="allow")


class NowApi(BaseModel):
    code: str
    now: Now

    model_config = ConfigDict(extra="allow")


class Daily(BaseModel):
    fxDate: str
    week: Optional[str] = None
    date: Optional[str] = None
    tempMax: str
    tempMin: str
    textDay: str
    textNight: str
    iconDay: str
    iconNight: str

    model_config = ConfigDict(extra="allow")


class DailyApi(BaseModel):
    code: str
    daily: list[Daily]

    model_config = ConfigDict(extra="allow")


class Air(BaseModel):
    category: str
    aqi: str
    pm2p5: str
    pm10: str
    o3: str
    co: str
    no2: str
    so2: str
    tag_color: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class AirApi(BaseModel):
    code: str
    now: Optional[Air] = None

    model_config = ConfigDict(extra="allow")


class Warning(BaseModel):
    title: str
    type: str
    pubTime: str
    text: str

    model_config = ConfigDict(extra="allow")


class WarningApi(BaseModel):
    code: str
    warning: Optional[list[Warning]] = None

    model_config = ConfigDict(extra="allow")


class Hourly(BaseModel):
    fxTime: str
    hour: Optional[str] = None
    temp: str
    icon: str
    text: str
    temp_percent: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class HourlyApi(BaseModel):
    code: str
    hourly: list[Hourly]

    model_config = ConfigDict(extra="allow")


class HourlyType(IntEnum):
    current_12h = 1
    current_24h = 2


class APIError(Exception): ...


class ConfigError(Exception): ...


class CityNotFoundError(Exception): ...


class QWeatherConfig(BaseModel):
    apihost: str = Field(default="https://api.qweather.com")
    apikey: Optional[str] = Field(
        default=None, deprecated="建议使用更安全的JWT key"
    )
    apitype: Optional[int] = Field(default=None)
    hourlytype: HourlyType = Field(default=HourlyType.current_12h)
    forecase_days: Optional[int] = Field(default=3)
    use_jwt: Optional[bool] = Field(
        default=True, description="是否使用 JWT，默认 True"
    )
    jwt_sub: Optional[str] = Field(
        default=None, description="JWT sub，即控制台中的项目ID"
    )
    jwt_private_key: Optional[str] = Field(
        default=None, deprecated="JWT 私钥文本，需要自行生成"
    )

    jwt_kid: Optional[str] = Field(
        default=None, description="JWT Key ID，即控制台中上传公钥后即可获取"
    )
    # debug: Optional[bool] = Field(default=False)
