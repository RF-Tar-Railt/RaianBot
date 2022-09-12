from arclet.alconna import Args, Empty, ArgField, CommandMeta
from arclet.alconna.graia import Alconna, alcommand, fetch_name
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, At
from graia.ariadne.util.saya import decorate
from graia.ariadne.app import Ariadne

from app import Sender, record
from modules.arknights.random import RandomOperator
from utils.generate_img import create_image


@record("随机干员")
@alcommand(
    Alconna(
        "测试干员",
        Args["name#你的代号是?", [str, At], ArgField(Empty, completion=lambda: "你的代号是?")],
        meta=CommandMeta("依据名字测试你会是什么干员", example="$测试干员 海猫")
    ), send_error=True
)
@decorate({"name": fetch_name()})
async def ro(app: Ariadne, sender: Sender, name: str):
    """依据名字随机生成干员"""
    return await app.send_message(
        sender,
        MessageChain(
            Image(data_bytes=(await create_image(RandomOperator().generate(name))))
        ),
    )
