import json
from typing import Union
from arclet.alconna import Args
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from app import RaianMain

bot = RaianMain.current()
channel = Channel.current()

weather = Alconna(
    "{city}天气",
    Args["time", ["今天", "明天", "后天", "大后天"], "今天"],
    headers=bot.config.command_prefix,
    help_text=f"查询某个城市的天气 Usage: 提供四个可查询的时间段; Example: {bot.config.command_prefix[0]}北京天气 明天;",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=weather, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def test2(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    arp = result.result
    city = arp.header['city']
    days_list = {'今天': 0, '明天': 1, '后天': 2, '大后天': 3, '老后天': 4}
    url = 'http://wthrcdn.etouch.cn/weather_mini?city=' + city
    days = days_list[arp.time]
    async with app.service.client_session.get(url, timeout=2) as response:
        d = json.loads(await response.text())
        if d['status'] != 1000:
            return await app.send_message(sender, MessageChain("不对劲。。。"))
        res = (
            f"城市：{d['data']['city']}\n"
            f"日期：{d['data']['forecast'][days]['date']}\n"
            f"天气：{d['data']['forecast'][days]['type']}\n"
            f"温度：{d['data']['forecast'][days]['high']}, {d['data']['forecast'][days]['low']}\n"
            f"提醒：{d['data']['ganmao']}"
        )
        return await app.send_message(sender, MessageChain(res))
