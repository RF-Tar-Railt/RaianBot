from typing import Union
from arclet.alconna import Args, Option
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne
import asyncio
from app import RaianMain

bot = RaianMain.current()
channel = Channel.current()

music = Alconna(
    "点歌",
    Args["name", str],
    options=[Option("歌手|s", Args['singer', str], dest="singer")],
    headers=bot.config.command_prefix,
    help_text=f"在网易云点歌 Usage: 用 歌手 选项指定歌手; Example: {bot.config.command_prefix[0]}点歌 Rise;",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=music, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage]))
async def song(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    arp = result.result
    singer = (singer + " ") if (singer := arp.query("singer.singer")) else ""
    song_search_url = f"http://music.eleuu.com/search?keywords={singer + arp.name}"
    try:
        async with app.service.client_session.get(song_search_url, timeout=20) as resp:
            data = await resp.json()
    except asyncio.TimeoutError:
        return await app.send_message(sender, MessageChain("服务器繁忙中"))
    if data["code"] != 200:
        return await app.send_message(sender, MessageChain(f"服务器返回错误：{data['message']}"))
    if data["result"]["songCount"] == 0:
        return await app.send_message(sender, MessageChain("没有搜索到呐~换一首歌试试吧！"))
    song_id = data["result"]["songs"][0]["id"]
    url = f"https://y.music.163.com/m/song?app_version=8.7.65&id={song_id}&userid=3269267634#?thirdfrom=qq"
    return await app.send_message(sender, MessageChain(url))
