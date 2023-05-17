from arclet.alconna import Alconna, Args, Empty, Field, CommandMeta
from arclet.alconna.graia import alcommand, fetch_name
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, At
from graiax.shortcut.saya import decorate
from graia.ariadne.app import Ariadne
from arknights_toolkit.random_operator import RandomOperator

from app import Sender, record, create_image, accessable, exclusive


@alcommand(
    Alconna(
        "测试干员",
        Args["name#你的代号", [str, At], Field(Empty, completion=lambda: "你的代号是?")],
        meta=CommandMeta("依据名字测试你会是什么干员", example="$测试干员 海猫"),
    ),
    send_error=True,
)
@decorate({"name": fetch_name()})
@record("随机干员")
@exclusive
@accessable
async def ro(app: Ariadne, sender: Sender, name: str):
    """依据名字随机生成干员"""
    return await app.send_message(
        sender,
        MessageChain(Image(data_bytes=(await create_image(RandomOperator().generate(name))))),
    )
