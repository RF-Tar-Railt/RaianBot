import asyncio

from arclet.alconna import Alconna, Args, CommandMeta, Field
from arclet.alconna.graia import Match, alcommand
from avilla.core import Context, MessageChain, MessageReceived
from avilla.elizabeth.account import ElizabethAccount
from avilla.standard.qq.elements import MusicShare, MusicShareKind

from app.client import AiohttpClientService
from app.interrupt import FunctionWaiter
from app.shortcut import accessable, allow, exclusive

from .config import MusicConfig

music = Alconna(
    "点歌",
    Args["name", str, Field(completion=lambda: "比如说, 以父之名")],
    Args["singer?", str, Field(completion=lambda: "比如说, 'Talyer Swift'")],
    meta=CommandMeta(
        "在网易云点歌",
        usage="可以指定歌手, 与歌名用空格分开",
        example="$点歌 Rise",
        extra={"supports": {"mirai"}},
    ),
)
JUMP_URL = "https://music.163.com/song?id={id}"
MUSIC_URL = "https://music.163.com/song/media/outer/url?id={id}.mp3"


@alcommand(music)
@allow(ElizabethAccount)
@exclusive
@accessable
async def song(ctx: Context, name: Match[str], singer: Match[str], config: MusicConfig, aio: AiohttpClientService):
    _singer = f"{singer.result} " if singer.available else ""
    api = config.api
    if not api:
        return await ctx.scene.send_message("网易云没有配置！")
    song_search_url = f"{api}/search?keywords={_singer + name.result}&limit=10"
    try:
        async with aio.session.get(song_search_url, timeout=20) as resp:
            data = await resp.json()
    except asyncio.TimeoutError:
        return await ctx.scene.send_message("服务器繁忙中")
    if data["code"] != 200:
        return await ctx.scene.send_message(f"服务器返回错误：{data['message']}")
    if (count := data["result"]["songCount"]) == 0:
        return await ctx.scene.send_message("没有搜索到呐~换一首歌试试吧！")
    index = 0
    if count > 1:
        await ctx.scene.send_message("查找到多首歌曲；请选择其中一首，限时 15秒")
        await ctx.scene.send_message(
            "\n".join(
                f"{str(index).rjust(len(str(count)), '0')}. "
                f"{slot['name']} - {', '.join(artist['name'] for artist in slot['artists'])}"
                for index, slot in enumerate(data["result"]["songs"])
            ),
        )

        async def waiter(waiter_ctx: Context, message: MessageChain):
            if waiter_ctx.client == ctx.client:
                return int(str(message)) if str(message).isdigit() else False

        res = await FunctionWaiter(
            waiter,
            [MessageReceived],
            block_propagation=ctx.client.follows("::friend") or ctx.client.follows("::guild.user"),
        ).wait(15)
        if res:
            index = res
    if index >= count:
        return await ctx.scene.send_message("别捣乱！")
    song_ = data["result"]["songs"][index]
    song_id = song_["id"]
    async with aio.session.get(f"{api}/song/detail?ids={song_id}", timeout=20) as resp:
        picture = (await resp.json())["songs"][0]["al"]["picUrl"]
    song_summary = f"{song_['name']}--{', '.join(artist['name'] for artist in song_['artists'])}"
    return await ctx.scene.send_message(
        MusicShare(
            kind=MusicShareKind.NeteaseCloudMusic,
            title=song_["name"],
            content=song_summary,
            url=JUMP_URL.format(id=song_id),
            brief=song_summary,
            thumbnail=picture,
            audio=MUSIC_URL.format(id=song_id),
        )
    )
