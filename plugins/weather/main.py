from pathlib import Path
from secrets import token_hex

import ujson
from app.core import RaianBotService
from app.shortcut import record, picture
from arclet.alconna import Alconna, Args, CommandMeta
from arclet.alconna.graia import Match, alcommand
from avilla.core import Context, Picture, RawResource
from graiax.playwright import PlaywrightBrowser, PlaywrightService
from library.heweather import CityNotFoundError, HeWeather, render

from .config import WeatherConfig

bot = RaianBotService.current()
config = bot.config.plugin.get(WeatherConfig)

cmd = Alconna(
    "天气",
    Args["city", str],
    meta=CommandMeta("查询某个城市的天气", example="$北京天气"),
)
cmd.shortcut(
    "(?P<city>.+)天气",
    {
        "fuzzy": False,
        "prefix": True,
        "command": "天气 {city}",
    },
)

if config.heweather:
    heweather = HeWeather(
        bot.config.platform.heweather_api_key, bot.config.platform.heweather_api_type, bot.config.proxy
    )
    cache_dir = Path(bot.config.data_dir) / "plugins" / "weather"
    cache_dir.mkdir(parents=True, exist_ok=True)

    @alcommand(cmd, remove_tome=True)
    @record("天气")
    # @exclusive
    # @accessable
    async def weather(ctx: Context, city: Match[str], pw: PlaywrightService):
        if not city.result:
            return await ctx.scene.send_message("地点是...空气吗?? >_<")
        try:
            data = await heweather.load_data(city.result)
        except CityNotFoundError:
            return await ctx.scene.send_message("不对劲。。。")
        file = cache_dir / f"{data.city_id}.html"
        with file.open("w+", encoding="utf-8") as f:
            f.write(await render(data, bot.config.platform.heweather_api_hourly_type))
        browser: PlaywrightBrowser = pw.get_interface(PlaywrightBrowser)
        page = await browser.new_page(
            viewport={"width": 1000, "height": 300},
            device_scale_factor=2,
        )
        await page.goto(file.absolute().as_uri())
        img = await page.screenshot(type="jpeg", quality=80, full_page=True, scale="device")
        await page.close()
        try:
            return await ctx.scene.send_message(Picture(RawResource(img)))
        except Exception:
            url = await bot.upload_to_cos(img, f"weather_{token_hex(16)}.jpg")
            return await ctx.scene.send_message(picture(url, ctx))


else:
    with (Path.cwd() / "assets" / "data" / "city.json").open("r", encoding="utf-8") as f:
        city_ids = ujson.load(f)

    @alcommand(cmd, remove_tome=True)
    @record("天气")
    # @exclusive
    # @accessable
    async def weather(ctx: Context, city: Match[str], pw: PlaywrightService):
        if city.result not in city_ids:
            return await ctx.scene.send_message("不对劲。。。")
        browser: PlaywrightBrowser = pw.get_interface(PlaywrightBrowser)
        page = await browser.new_page()
        await page.click("html")
        await page.goto(f"https://m.weather.com.cn/mweather/{city_ids[city.result]}.shtml")
        ad = page.locator("//div[@class='guanggao']")
        await ad.first.evaluate("node => node.remove()")
        elem1 = page.locator("//div[@class='npage1']")
        bounding1 = await elem1.bounding_box()
        elem2 = page.locator("//div[@class='h40']")
        if await elem2.count():
            bounding2 = await elem2.first.bounding_box()
            bounding1["height"] += bounding2["height"]
        elem3 = page.locator("//div[@class='weatherCardTop']")
        if await elem3.count():
            bounding3 = await elem3.first.bounding_box()
            bounding1["height"] += bounding3["height"]
        elem4 = page.locator("//div[@class='h15']")
        if await elem4.count():
            bounding3 = await elem4.first.bounding_box()
            bounding1["height"] += bounding3["height"]
        img = await page.screenshot(full_page=True, clip=bounding1)
        await page.close()
        try:
            return await ctx.scene.send_message(Picture(RawResource(img)))
        except Exception:
            url = await bot.upload_to_cos(img, f"weather_{token_hex(16)}.jpg")
            return await ctx.scene.send_message(picture(url, ctx))
