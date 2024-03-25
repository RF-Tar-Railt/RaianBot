from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
