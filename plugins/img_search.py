import asyncio
from typing import Optional
from contextlib import suppress
from PicImageSearch import Ascii2D, SauceNAO, Network, Iqdb
from PicImageSearch.saucenao import SauceNAOResponse
from PicImageSearch.ascii2d import Ascii2DResponse
from PicImageSearch.iqdb import IqdbResponse
from arclet.alconna import Args, CommandMeta
from arclet.alconna.graia import Alconna, Match, alcommand
from arclet.alconna.ariadne import ImgOrUrl
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.element import Image, Source, Forward, ForwardNode, Plain
from graia.ariadne.app import Ariadne
from graia.ariadne.util.interrupt import FunctionWaiter
from loguru import logger

from app import Sender, Target, record, accessable, exclusive
from plugins.config.img_search import ImgSearchConfig

running = asyncio.Event()

search = Alconna(
    "搜图",
    Args["img;?", ImgOrUrl],
    meta=CommandMeta("以图搜图，搜图结果会自动发送给你。", usage="该功能会尝试在三类搜索网站中搜索相似图片", example="$搜图 [图片]"),
)


@alcommand(search, send_error=True)
@record("搜图")
@exclusive
@accessable
async def saucenao(
    app: Ariadne, sender: Sender, target: Target, source: Source, img: Match[str], config: ImgSearchConfig
):
    """通过各API搜图源"""

    # @Waiter.create_using_function(listening_events=[GroupMessage, FriendMessage])
    async def waiter1(app1: Ariadne, waiter1_sender: Sender, waiter1_target: Target, waiter1_message: MessageChain):
        if all([waiter1_sender.id == sender.id, waiter1_target.id == target.id]):
            waiter1_saying = waiter1_message.display
            if waiter1_saying == "取消":
                return False
            elif waiter1_message.has(Image):
                return waiter1_message.get_first(Image).url
            else:
                await app1.send_message(sender, MessageChain("请发送图片"))

    if running.is_set():
        await app.send_message(sender, MessageChain("以图搜图正在运行，请稍后再试"))
        return
    if img.available and img.result:
        image_url = img.result
    else:
        waite = await app.send_message(sender, MessageChain("请发送图片以继续，发送取消可终止搜图"))
        image_url = await FunctionWaiter(waiter1, [GroupMessage, FriendMessage]).wait(20, "None")
        if not image_url:
            return await app.send_message(sender, MessageChain("已取消"))
        if image_url == "None":
            return await app.send_message(sender, MessageChain("等待超时"), quote=waite.id)
    await app.send_message(sender, MessageChain("正在搜索，请稍后"), quote=source.id)
    running.set()
    sauce_result = None
    ascii2_result = None
    iqdb_result = None
    with suppress(RuntimeError):
        client = Network().start()
        sauce = SauceNAO(
            client=client,
            api_key=config.saucenao,
            numres=6,
            hide=0,
        )
        try:
            sauce_result: Optional[SauceNAOResponse] = await asyncio.wait_for(sauce.search(image_url), timeout=20)
        except Exception as e:
            logger.warning(e)
        if config.ascii2d:
            ascii2 = Ascii2D(client=client)
            try:
                ascii2_result: Optional[Ascii2DResponse] = await asyncio.wait_for(ascii2.search(image_url), timeout=20)
            except Exception as e:
                logger.warning(e)
        if config.iqdb:
            iqdb = Iqdb(client=client)
            try:
                iqdb_result: Optional[IqdbResponse] = await asyncio.wait_for(iqdb.search(image_url), timeout=20)
            except Exception as e:
                logger.warning(e)
        await client.close()
    if all([not sauce_result, not ascii2_result, not iqdb_result]):
        running.clear()
        return await app.send_message(sender, MessageChain("搜索失败, 未找到有价值的数据. 请尝试重新搜索"), quote=source.id)
    results = []
    if sauce_result:
        sauce_list = []
        for result in sauce_result.raw[:4]:
            sauce_list.append(
                ForwardNode(
                    target=target,
                    time=source.time,
                    message=MessageChain(
                        Image(url=result.thumbnail),
                        Plain(
                            f"\n相似度：{result.similarity}%"
                            f"\n标题：{result.title}"
                            f"\n节点名：{result.index_name}"
                            f"\n链接：{result.url}"
                        ),
                    ),
                )
            )
        results.append(ForwardNode(target=target, time=source.time, message=MessageChain(Forward(*sauce_list))))
    if ascii2_result:
        ascii2_list = []
        for result in ascii2_result.raw[:4]:
            ascii2_list.append(
                ForwardNode(
                    target=target,
                    time=source.time,
                    message=MessageChain(
                        Image(url=result.thumbnail),
                        Plain(f"\n标题：{result.title}" f"\n作者：{result.author}" f"\n链接：{result.url}"),
                    ),
                )
            )
        results.append(ForwardNode(target=target, time=source.time, message=MessageChain(Forward(*ascii2_list))))
    if iqdb_result:
        iqdb_list = []
        for result in iqdb_result.raw[:4]:
            iqdb_list.append(
                ForwardNode(
                    target=target,
                    time=source.time,
                    message=MessageChain(
                        Image(url=result.thumbnail),
                        Plain(
                            f"\n相似度：{result.similarity}"
                            f"\n来源：{result.source}"
                            f"\n备注：{result.content}"
                            f"\n链接：{result.url}"
                        ),
                    ),
                )
            )
        results.append(ForwardNode(target=target, time=source.time, message=MessageChain(Forward(*iqdb_list))))
    try:
        res = await app.send_message(
            sender,
            MessageChain(
                Forward(ForwardNode(target=target, message=MessageChain("搜索结果："), time=source.time), *results)
            ),
            quote=source.id,
        )
        if res.id < 0:
            await app.send_message(sender, MessageChain("搜图结果存在敏感信息，搜索失败"))
    finally:
        running.clear()
