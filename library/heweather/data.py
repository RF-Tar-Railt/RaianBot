import asyncio
from dataclasses import dataclass
from typing import Optional, Union

from httpx import AsyncClient, Response
from httpx._types import ProxiesTypes
from loguru import logger

from .model import AirApi, DailyApi, HourlyApi, NowApi, WarningApi


class APIError(Exception):
    ...


class ConfigError(Exception):
    ...


class CityNotFoundError(Exception):
    ...


@dataclass
class HeWeatherData:
    name: str
    city_id: str
    now: NowApi
    daily: DailyApi
    air: AirApi
    warning: WarningApi
    hourly: HourlyApi

    def __post_init__(self):
        if self.now.code == "200" and self.daily.code == "200":
            pass
        else:
            raise APIError(
                "错误! 请检查配置! "
                f"错误代码: now: {self.now.code}  "
                f"daily: {self.daily.code}  "
                + "air: {}  ".format(self.air.code if self.air else "None")
                + "warning: {}".format(self.warning.code if self.warning else "None")
                + "\n请参考: https://dev.qweather.com/docs/start/status-code/"
            )


class HeWeather:
    def __url__(self):
        self.url_geoapi = "https://geoapi.qweather.com/v2/city/"
        if self.api_type == 2 or self.api_type == 1:
            self.url_weather_api = "https://api.qweather.com/v7/weather/"
            self.url_weather_warning = "https://api.qweather.com/v7/warning/now"
            self.url_air = "https://api.qweather.com/v7/air/now"
            self.url_hourly = "https://api.qweather.com/v7/weather/24h"
            self.forecast_days = 7
            # if self.api_type == 1:
            logger.info("使用标准订阅API")
            # else:
            #     logger.info("使用商业版API")
        elif self.api_type == 0:
            self.url_weather_api = "https://devapi.qweather.com/v7/weather/"
            self.url_weather_warning = "https://devapi.qweather.com/v7/warning/now"
            self.url_air = "https://devapi.qweather.com/v7/air/now"
            self.url_hourly = "https://devapi.qweather.com/v7/weather/24h"
            self.forecast_days = 3
            logger.info("使用免费订阅API")
        else:
            raise ConfigError(
                "api_type 必须是为 (int)0 -> 免费订阅, (int)1 -> 标准订阅, (int)2 -> 商业版"
                f"\n当前为: ({type(self.api_type)}){self.api_type}"
            )

    def __init__(self, api_key: str, api_type: Union[int, str] = 0, proxies: Optional[ProxiesTypes] = None):
        self.apikey = api_key
        self.api_type = int(api_type)
        self.proxies = proxies
        self.__url__()

    async def load_data(self, city_name: str) -> HeWeatherData:
        city_id = await self._get_city_id(city_name)
        return HeWeatherData(
            city_name,
            city_id,
            *(
                await asyncio.gather(
                    self.now(city_id),
                    self.daily(city_id),
                    self.air(city_id),
                    self.warning(city_id),
                    self.hourly(city_id),
                )
            ),
        )

    async def _get_data(self, url: str, params: dict) -> Response:
        async with AsyncClient(proxies=self.proxies) as client:
            res = await client.get(url, params=params)
        return res

    async def _get_city_id(self, city_name: str, api_type: str = "lookup"):
        res = await self._get_data(
            url=self.url_geoapi + api_type,
            params={"location": city_name, "key": self.apikey, "number": 1},
        )

        res = res.json()
        logger.debug(res)
        if res["code"] == "404":
            raise CityNotFoundError()
        elif res["code"] != "200":
            raise APIError(
                "错误! 错误代码: {}".format(res["code"]) + "\n请参考: https://dev.qweather.com/docs/start/status-code/"
            )
        else:
            self.city_name = res["location"][0]["name"]
            return res["location"][0]["id"]

    def _check_response(self, response: Response) -> bool:
        if response.status_code == 200:
            logger.debug(f"{response.json()}")
            return True
        else:
            raise APIError(f"Response code:{response.status_code}")

    async def now(self, city_id: str) -> NowApi:
        res = await self._get_data(
            url=self.url_weather_api + "now",
            params={"location": city_id, "key": self.apikey},
        )
        self._check_response(res)
        return NowApi(**res.json())

    async def daily(self, city_id: str) -> DailyApi:
        res = await self._get_data(
            url=self.url_weather_api + str(self.forecast_days) + "d",
            params={"location": city_id, "key": self.apikey},
        )
        self._check_response(res)
        return DailyApi(**res.json())

    async def air(self, city_id: str) -> AirApi:
        res = await self._get_data(
            url=self.url_air,
            params={"location": city_id, "key": self.apikey},
        )
        self._check_response(res)
        return AirApi(**res.json())

    async def warning(self, city_id: str) -> Optional[WarningApi]:
        res = await self._get_data(
            url=self.url_weather_warning,
            params={"location": city_id, "key": self.apikey},
        )
        self._check_response(res)
        return None if res.json().get("code") == "204" else WarningApi(**res.json())

    async def hourly(self, city_id: str) -> HourlyApi:
        res = await self._get_data(
            url=self.url_hourly,
            params={"location": city_id, "key": self.apikey},
        )
        self._check_response(res)
        return HourlyApi(**res.json())
