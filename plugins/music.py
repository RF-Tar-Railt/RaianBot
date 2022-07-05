from arclet.alconna import Args, Option, Arpamar
from arclet.alconna.graia import Alconna
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.app import Ariadne
import asyncio

from app import command, Sender

music = Alconna(
    "点歌",
    Args["name", str],
    options=[Option("歌手|s", Args['singer', str], dest="singer")],
    help_text=f"在网易云点歌 Usage: 用 歌手 选项指定歌手; Example: $点歌 Rise;",
)


@command(music)
async def song(app: Ariadne, sender: Sender, result: Arpamar):
    singer = (singer + " ") if (singer := result.query("singer.singer")) else ""
    song_search_url = f"http://music.eleuu.com/search?keywords={singer + result.name}"
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
