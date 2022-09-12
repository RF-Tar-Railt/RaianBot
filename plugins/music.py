from arclet.alconna import Args, Option, Arpamar, ArgField, CommandMeta
from arclet.alconna.graia import Alconna, alcommand
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import MusicShare, MusicShareKind
from graia.ariadne.app import Ariadne
import asyncio

from app import Sender

music = Alconna(
    "点歌", Args["name", str, ArgField(completion=lambda: "比如说, ‘以父之名’")],
    options=[Option("歌手|-s", Args['singer', str], dest="singer")],
    meta=CommandMeta("在网易云点歌", usage="用 歌手 选项指定歌手", example="$点歌 Rise")
)
JUMP_URL = "https://music.163.com/song?id={id}"
MUSIC_URL = "https://music.163.com/song/media/outer/url?id={id}.mp3"


@alcommand(music)
async def song(app: Ariadne, sender: Sender, result: Arpamar):
    singer = f"{singer} " if (singer := result.query("singer.singer")) else ""
    song_search_url = f"http://localhost:4000/search?keywords={singer + result.name}&limit=10"
    try:
        async with app.service.client_session.get(song_search_url, timeout=20) as resp:
            data = await resp.json()
    except asyncio.TimeoutError:
        return await app.send_message(sender, MessageChain("服务器繁忙中"))
    if data["code"] != 200:
        return await app.send_message(sender, MessageChain(f"服务器返回错误：{data['message']}"))
    if data["result"]["songCount"] == 0:
        return await app.send_message(sender, MessageChain("没有搜索到呐~换一首歌试试吧！"))
    song_ = data["result"]["songs"][0]
    song_id = song_["id"]
    picture = song_["album"]["artist"]["img1v1Url"]
    song_summary = (
        f"{song_['name']}--{', '.join(artist['name'] for artist in song_['artists'])}"
    )
    return await app.send_message(sender, MessageChain(
        MusicShare(
            kind=MusicShareKind.NeteaseCloudMusic,
            title=song_['name'],
            summary=song_summary,
            jumpUrl=JUMP_URL.format(id=song_id),
            brief=song_summary,
            pictureUrl=picture,
            musicUrl=MUSIC_URL.format(id=song_id)
        )
    ))
