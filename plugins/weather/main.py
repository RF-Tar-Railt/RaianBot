from __future__ import annotations

from pathlib import Path
from secrets import token_hex

import ujson
from arclet.alconna import Alconna, Args, CommandMeta, Field
from arclet.alconna.graia import Match, alcommand
from avilla.core import Context, Notice, Picture, RawResource
from avilla.qqapi.exception import ActionFailed
from avilla.standard.core.message import MessageReceived
from graia.amnesia.message import MessageChain
from graiax.playwright import PlaywrightBrowser, PlaywrightService

from app.core import RaianBotService
from app.interrupt import FunctionWaiter
from app.shortcut import accessable, exclusive, picture, record
from library.heweather import CityNotFoundError, HeWeather, render

from .config import WeatherConfig

bot = RaianBotService.current()
config = bot.config.plugin.get(WeatherConfig)

cmd = Alconna(
    "天气",
    Args["city?", str, Field(unmatch_tips=lambda x: f"请输入城市名字，而不是{x}")],
    meta=CommandMeta("查询某个城市的天气", example="$天气 北京\n$北京天气", extra={"supports": {"mirai", "qqapi"}}),
)
cmd.shortcut(
    "(?P<city>.+)天气",
    {
        "fuzzy": False,
        "prefix": True,
        "command": "天气 {city}",
    },
)

if config.heweather and bot.config.platform.heweather_api_key and bot.config.platform.heweather_api_type is not None:
    heweather = HeWeather(
        bot.config.platform.heweather_api_key, bot.config.platform.heweather_api_type, bot.config.proxy
    )
    cache_dir = Path(bot.config.data_dir) / "plugins" / "weather"
    cache_dir.mkdir(parents=True, exist_ok=True)

    @alcommand(cmd, post=True, send_error=True)
    @record("天气")
    @exclusive
    @accessable
    async def weather(ctx: Context, city: Match[str], pw: PlaywrightService):
        if city.available:
            city_name = city.result
        else:
            await ctx.scene.send_message("请输入地点名称：\n如 [回复机器人] 北京")

            async def waiter(waiter_ctx: Context, message: MessageChain):
                name = str(message.exclude(Notice)).lstrip()
                if waiter_ctx.scene.pattern == ctx.scene.pattern:
                    return name

            city_name: str | None = await FunctionWaiter(
                waiter,
                [MessageReceived],
                block_propagation=ctx.client.follows("::friend") or ctx.client.follows("::guild.user"),
            ).wait(timeout=30, default=None)
            if city_name is None:
                return await ctx.scene.send_message("等待已超时，取消查询。")
        try:
            data = await heweather.load_data(city_name)
        except CityNotFoundError:
            return await ctx.scene.send_message("地点是...空气吗?? >_<")
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
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed as e:
                return await ctx.scene.send_message(f"图片发送失败:\ncode: {e.code}\nmsg: {e.message}")

else:
    with (Path.cwd() / "assets" / "data" / "city.json").open("r", encoding="utf-8") as f:
        city_ids = ujson.load(f)

    @alcommand(cmd, post=True, send_error=True)
    @record("天气")
    @exclusive
    @accessable
    async def weather(ctx: Context, city: Match[str], pw: PlaywrightService):
        if city.available:
            city_name = city.result
        else:
            await ctx.scene.send_message("请输入地点名称：\n如 [回复机器人] 北京")

            async def waiter(waiter_ctx: Context, message: MessageChain):
                name = str(message.exclude(Notice)).lstrip()
                if waiter_ctx.scene.pattern == ctx.scene.pattern:
                    return name

            city_name: str | None = await FunctionWaiter(
                waiter,
                [MessageReceived],
                block_propagation=ctx.client.follows("::friend") or ctx.client.follows("::guild.user"),
            ).wait(timeout=30, default=None)
            if city_name is None:
                return await ctx.scene.send_message("等待已超时，取消查询。")
        if city_name not in city_ids:
            return await ctx.scene.send_message("地点是...空气吗?? >_<")
        browser: PlaywrightBrowser = pw.get_interface(PlaywrightBrowser)
        page = await browser.new_page()
        await page.click("html")
        await page.goto(f"https://m.weather.com.cn/mweather/{city_ids[city_name]}.shtml")
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
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed as e:
                return await ctx.scene.send_message(f"图片发送失败:\ncode: {e.code}\nmsg: {e.message}")
