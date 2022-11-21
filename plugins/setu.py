from arclet.alconna import Args, Option, CommandMeta, Arpamar
from arclet.alconna.graia import Alconna, alcommand
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.app import Ariadne

from app import record, Sender, Target

setu = Alconna(
    "涩图",
    Option("-r18", help_text="是否查找r18涩图"),
    Option("-tag", Args["tags;S", str], help_text="关键字"),
    meta=CommandMeta("顾名思义"),
)


@alcommand(setu)
@record('setu')
async def send_setu(app: Ariadne, target: Target, sender: Sender, result: Arpamar):
    """随机涩图发送"""
    data={"r18": 2 if result.find("r18") else 0}
    if result.find("tag"):
        data["tag"] = list(result.query_with(tuple, "tag.tags", ()))
    async with app.service.client_session.post(
        "https://api.lolicon.app/setu/v2?",
        headers={"Content-type": "application/json", "accept": "application/json"},
        json=data,
        timeout=20,
    ) as resp:
        res = await resp.json()
    if res.get("error"):
        return await app.send_message(sender, MessageChain("网路出错了！呜"))

    async with app.service.client_session.get(
            f"https://pixiv.re/{res['data'][0]['pid']}.{res['data'][0]['ext']}"
    ) as img:
        bts = await img.read()
    await app.send_message(sender, MessageChain(
        f"标题：{res['data'][0]['title']}\n"
        f"pid：{res['data'][0]['pid']}\n"
        f"tags：{', '.join(res['data'][0]['tags'][:4])}"
    ))
    res = await app.send_message(sender, MessageChain(Image(data_bytes=bts)))
    if res.id < 0:
        return await app.send_message(sender, MessageChain("图片发不出来，抱歉。。"))
