import random
from arclet.alconna import Args, Option, Arpamar
from datetime import datetime
from arclet.alconna.graia import Alconna, command, Match
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Forward, ForwardNode, Image
from graia.ariadne.app import Ariadne

from app import record, Sender, Target

setu = Alconna(
    "涩图",
    Args["r_per", ["r9", "r16", "r18"], "r9"],
    help_text="顾名思义",
    options=[Option("tag", Args["tag", str])],
    action=lambda x: ({"r9": 2, "r16": 4, "r18": 6})[x]
)


@record('setu')
@command(setu)
async def send_setu(app: Ariadne, target: Target, sender: Sender, r_per: Match[int], result: Arpamar):
    """随机涩图发送"""
    async with app.service.client_session.request(
            "GET",
            (
                f"https://api.a60.one:8443/get/tags/{result.query('tag.tag', '美图')}"
                f"?num={random.randint(1, 5)}&san={r_per}"
                if result.find("tag") else
                f"https://api.a60.one:8443/?num={random.randint(1, 5)}&san={r_per}"
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
