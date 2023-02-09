from arclet.alconna import Args, Field, CommandMeta
from arclet.alconna.graia import Alconna, alcommand, Match
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import MusicShare, MusicShareKind
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.model.relationship import Friend
from graia.ariadne.app import Ariadne
from graia.ariadne.util.interrupt import FunctionWaiter
import asyncio

from app import Sender, Target, exclusive, accessable
from plugins.config.music import MusicConfig

music = Alconna(
    "点歌",
    Args["name", str, Field(completion=lambda: "比如说, ‘以父之名’")],
    Args["singer;?", str, Field(completion=lambda: "比如说, ‘周杰伦’")],
    meta=CommandMeta("在网易云点歌", usage="可以指定歌手, 与歌名用空格分开", example="$点歌 Rise"),
)
JUMP_URL = "https://music.163.com/song?id={id}"
MUSIC_URL = "https://music.163.com/song/media/outer/url?id={id}.mp3"


@alcommand(music)
@exclusive
@accessable
async def song(app: Ariadne, sender: Sender, target: Target, name: Match[str], singer: Match[str], config: MusicConfig):
    _singer = f"{singer.result} " if singer.available else ""
    api = config.api
    if not api:
        return await app.send_message(sender, "网易云没有配置！")
    song_search_url = f"{api}/search?keywords={_singer + name.result}&limit=10"
    try:
        async with app.service.client_session.get(song_search_url, timeout=20) as resp:
            data = await resp.json()
    except asyncio.TimeoutError:
        return await app.send_message(sender, MessageChain("服务器繁忙中"))
    if data["code"] != 200:
        return await app.send_message(sender, MessageChain(f"服务器返回错误：{data['message']}"))
    if (count := data["result"]["songCount"]) == 0:
        return await app.send_message(sender, MessageChain("没有搜索到呐~换一首歌试试吧！"))
    index = 0
    if count > 1:
        await app.send_message(sender, MessageChain("查找到多首歌曲；请选择其中一首，限时 15秒"))
        await app.send_message(
            sender,
            "\n".join(
                f"{str(index).rjust(len(str(count)), '0')}. {slot['name']} - {', '.join(artist['name'] for artist in slot['artists'])}"
                for index, slot in enumerate(data["result"]["songs"])
            ),
        )

        async def waiter(waiter_sender: Sender, waiter_target: Target, message: MessageChain):
            if sender.id == waiter_sender.id and waiter_target.id == target.id:
                return int(str(message)) if str(message).isdigit() else False

        res = await FunctionWaiter(
            waiter, [FriendMessage, GroupMessage], block_propagation=isinstance(sender, Friend)
        ).wait(15)
        if res:
            index = res
    if index >= count:
        return await app.send_message(sender, "别捣乱！")
    song_ = data["result"]["songs"][index]
    song_id = song_["id"]
    async with app.service.client_session.get(f"{api}/song/detail?ids={song_id}", timeout=20) as resp:
        picture = (await resp.json())["songs"][0]["al"]["picUrl"]
    song_summary = f"{song_['name']}--{', '.join(artist['name'] for artist in song_['artists'])}"
    return await app.send_message(
        sender,
        MessageChain(
            MusicShare(
                kind=MusicShareKind.NeteaseCloudMusic,
                title=song_["name"],
                summary=song_summary,
                jumpUrl=JUMP_URL.format(id=song_id),
                brief=song_summary,
                pictureUrl=picture,
                musicUrl=MUSIC_URL.format(id=song_id),
            )
        ),
    )
