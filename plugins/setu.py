import random
from aiohttp import ClientSession
from arclet.alconna import Args, Option
from datetime import datetime
from arclet.alconna.graia import Alconna
from arclet.alconna.graia.dispatcher import AlconnaProperty
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Forward, ForwardNode, Image
from graia.ariadne.event.message import MessageEvent
from graia.ariadne.app import Ariadne

from app import record, command, Sender

setu = Alconna(
    "涩图",
    Args["r-per", ["r9", "r16", "r18"], "r9"],
    help_text=f"顾名思义",
    options=[Option("tag", Args["tag", str])]
)


@record('setu')
@command(setu)
async def send_setu(
        app: Ariadne,
        sender: Sender,
        result: AlconnaProperty[MessageEvent]
):
    """随机涩图发送"""
    target = result.source.sender
    arp = result.result
    san = ({"r9": 2, "r16": 4, "r18": 6})[arp.query("r-per", 'r9')]
    async with ClientSession() as session:
        async with session.request(
                "GET",
                (
                    f"https://api.a60.one:8443/get/tags/{arp.query('tag.tag', '美图')}"
                    f"?num={random.randint(1, 5)}&san={san}"
                    if arp.find("tag") else
                    f"https://api.a60.one:8443/?num={random.randint(1, 5)}&san={san}"
                ),
                timeout=20
        ) as resp:
            data = await resp.json()
    if data.get("code", False) != 200:
        return await app.send_message(sender, MessageChain("网路出错了！呜"))
    nodes = [
        ForwardNode(
            target=target, time=datetime.now(),
            message=MessageChain("涩图来了！")
        )
    ]
    for pic in data['data']['imgs']:
        nodes.append(
            ForwardNode(
                target=target, time=datetime.now(),
                message=MessageChain(f"ID: {pic['pic']}\nName: {pic['name']}")
            )
        )
        nodes.append(
            ForwardNode(
                target=target, time=datetime.now(),
                message=MessageChain(Image(url=pic['url']))
            )
        )
    res = await app.send_message(sender, MessageChain(Forward(*nodes)))
    if res.messageId < 0:
        return await app.send_message(sender, MessageChain("图片发不出来，抱歉。。"))
