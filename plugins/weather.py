import json
from arclet.alconna import Args, Arpamar, ArgField, CommandMeta
from arclet.alconna.graia import Alconna, command, Match
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.app import Ariadne

from app import Sender


@command(
    Alconna(
        "{city}?天气",
        Args[
            "time",
            {"今天": 0, "明天": 1, "后天": 2, "大后天": 3, "老后天": 4},
            ArgField(0, alias="今天", completion=lambda: "试试五个时间段:\n - 今天\n - 明天\n - 后天\n - 大后天\n - 老后天"),
        ],
        meta=CommandMeta("查询某个城市的天气", usage="提供五个可查询的时间段", example="$北京天气 明天"),
    )
)
async def weather(app: Ariadne, sender: Sender, time: Match[int], result: Arpamar):
    city = result.header["city"] or "长沙"
    url = f"http://wthrcdn.etouch.cn/weather_mini?city={city}"
    async with app.service.client_session.get(url, timeout=2) as response:
        d = json.loads(await response.text())
        if d["status"] != 1000:
            return await app.send_message(sender, MessageChain("不对劲。。。"))
        res = (
            f"城市：{d['data']['city']}\n"
            f"日期：{d['data']['forecast'][time.result]['date']}\n"
            f"天气：{d['data']['forecast'][time.result]['type']}\n"
            f"温度：{d['data']['forecast'][time.result]['high']}, {d['data']['forecast'][time.result]['low']}\n"
            f"提醒：{d['data']['ganmao']}"
        )
        return await app.send_message(sender, MessageChain(res))
