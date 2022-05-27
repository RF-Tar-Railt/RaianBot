import asyncio

from PicImageSearch import Ascii2D, SauceNAO, Network, Iqdb
from arclet.alconna import Args
from arclet.alconna.graia.saya import AlconnaSchema
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.element import Image, Source, Forward, ForwardNode, Plain
from graia.ariadne.model import Group, Member
from graia.ariadne.app import Ariadne
from graia.broadcast.interrupt import InterruptControl, Waiter

from app import RaianMain

bot = RaianMain.current()
channel = Channel.current()
inc = InterruptControl(bot.broadcast)
running = asyncio.Event()

search = Alconna(
    "搜图", Args["img;O":[Image, 'url']],
    headers=bot.config.command_prefix,
    help_text=f"以图搜图，搜图结果会自动发送给你。Usage: 该功能会尝试在三类搜索网站中搜索相似图片 ; Example: {bot.config.command_prefix[0]}搜图 [图片];"
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=search, help_flag='reply')))
@channel.use(ListenerSchema([GroupMessage]))
async def saucenao(app: Ariadne, group: Group, member: Member, source: Source, result: AlconnaProperty):
    @Waiter.create_using_function(listening_events=[GroupMessage])
    async def waiter1(
            app1: Ariadne,
            waiter1_group: Group, waiter1_member: Member, waiter1_message: MessageChain
    ):
        if all([waiter1_group.id == group.id, waiter1_member.id == member.id]):
            waiter1_saying = waiter1_message.asDisplay()
            if waiter1_saying == "取消":
                return False
            elif waiter1_message.has(Image):
                return waiter1_message.getFirst(Image).url
            else:
                await app1.sendGroupMessage(group, MessageChain.create("请发送图片"))

    if running.is_set():
        await app.sendGroupMessage(
            group, MessageChain.create("以图搜图正在运行，请稍后再试")
        )
        return
    arp = result.result
    if img := arp.main_args.get('img', None):
        image_url = img if isinstance(img, str) else img.url

    else:
        waite = await app.sendGroupMessage(
            group, MessageChain.create("请发送图片以继续，发送取消可终止搜图")
        )
        try:
            image_url = await inc.wait(waiter1, timeout=20)  # type: ignore
            if not image_url:
                return await app.sendGroupMessage(
                    group, MessageChain.create("已取消")
                )
        except asyncio.TimeoutError:
            return await app.sendGroupMessage(
                group, MessageChain.create("等待超时"), quote=waite.messageId
            )
    await app.sendGroupMessage(
        group, MessageChain.create("正在搜索，请稍后"), quote=source.id
    )
    running.set()
    async with Network() as client:
        sauce = SauceNAO(client=client, api_key=bot.config.plugin['saucenao'])
        ascii2 = Ascii2D(client=client)
        iqdb = Iqdb(client=client)

        try:
            sauce_result = await asyncio.wait_for(sauce.search(image_url), timeout=20)
        except Exception:
            sauce_result = None
        try:
            ascii2_result = await asyncio.wait_for(ascii2.search(image_url), timeout=20)
        except Exception:
            ascii2_result = None
        try:
            iqdb_result = await asyncio.wait_for(iqdb.search(image_url), timeout=20)
        except Exception:
            iqdb_result = None
        if all([not sauce_result, not ascii2_result, not iqdb_result]):
            running.clear()
            return await app.sendGroupMessage(
                group, MessageChain.create(f"搜索失败, 未找到有价值的数据. 请尝试重新搜索"), quote=source.id
            )
        results = []
        if sauce_result:
            sauce_list = []
            for result in sauce_result.raw[:2]:
                sauce_list.append(
                    ForwardNode(
                        target=member,
                        time=source.time,
                        message=MessageChain.create(
                            [
                                Image(url=result.thumbnail),
                                Plain(
                                    f"\n相似度：{result.similarity}%"
                                    f"\n标题：{result.title}"
                                    f"\n节点名：{result.index_name}"
                                    f"\n链接：{result.url}"
                                )
                            ]
                        )
                    )
                )
            results.append(
                ForwardNode(target=member, time=source.time, message=MessageChain.create(Forward(*sauce_list)))
            )

        if ascii2_result:
            ascii2_list = []
            for result in ascii2_result.raw[:2]:
                ascii2_list.append(
                    ForwardNode(
                        target=member,
                        time=source.time,
                        message=MessageChain.create(
                            [
                                Image(url=result.thumbnail),
                                Plain(
                                    f"\n标题：{result.title}"
                                    f"\n作者：{result.author}"
                                    f"\n链接：{result.url}"
                                )
                            ]
                        )
                    )
                )
            results.append(
                ForwardNode(target=member, time=source.time, message=MessageChain.create(Forward(*ascii2_list)))
            )
        if iqdb_result:
            iqdb_list = []
            for result in iqdb_result.raw[:2]:
                iqdb_list.append(
                    ForwardNode(
                        target=member,
                        time=source.time,
                        message=MessageChain.create(
                            [
                                Image(url=result.thumbnail),
                                Plain(
                                    f"\n相似度：{result.similarity}"
                                    f"\n来源：{result.source}"
                                    f"\n备注：{result.content}"
                                    f"\n链接：{result.url}"
                                )
                            ]
                        )
                    )
                )
            results.append(
                ForwardNode(target=member, time=source.time, message=MessageChain.create(Forward(*iqdb_list)))
            )
        try:
            await app.sendGroupMessage(
                group,
                MessageChain.create(
                    [
                        Forward(
                            ForwardNode(target=member, message=MessageChain.create("搜索结果："), time=source.time),
                            *results
                        )
                    ]
                ),
                quote=source.id,
            )
        finally:
            running.clear()
