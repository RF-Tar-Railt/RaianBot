import re
from typing import Tuple

from aiohttp import ClientSession, TCPConnector
from arclet.alconna import Alconna, Args, Field, CommandMeta, Option, MultiVar
from arclet.alconna.graia import alcommand, Match, assign
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.app import Ariadne
from graia.ariadne.message.element import Voice
from graiax.silkcoder import async_encode
from app import Sender, accessable, exclusive

character = {
    0: "綾地寧々",
    1: "因幡めぐる",
    2: "朝武芳乃",
    3: "常陸茉子",
    4: "ムラサメ",
    5: "鞍馬小春",
    6: "在原七海",
    7: "和泉妃愛",
    8: "常盤華乃",
    9: "錦あすみ",
    10: "鎌倉詩桜",
    11: "竜閑天梨",
    12: "和泉里",
    13: "新川広夢",
    14: "聖莉々子",
}

jp = Alconna(
    "日本语",
    Args["jptext", MultiVar(str, "+"), Field(completion=lambda: "比如说，daisuki")],
    Option(
        "moe",
        Args[
            "char",
            int,
            Field(
                0,
                alias="綾地寧々",
                completion=lambda: [f"{v}: {k}" for k, v in character.items()],
            ),
        ],
        help_text="使用vits生成语音\n可使用角色与对应id：\n"
        + "\n".join([f"    {v}: {k}" for k, v in character.items()]),
    ),
    meta=CommandMeta("日本语本当上手", usage="日语文本的tts", example="$日本语 suki"),
)


@alcommand(jp)
@assign("$main")
@exclusive
@accessable
async def tts(app: Ariadne, sender: Sender, jptext: Match[Tuple[str, ...]]):
    sentence = " ".join(jptext.result)
    if not sentence.strip() or re.search(r"[\d_+=\-/@#$%^&*(){}\[\]|\\]", sentence):
        return await app.send_message(sender, "无效的文本")
    async with ClientSession(
        connector=TCPConnector(limit=64, verify_ssl=False)
    ) as session:
        try:
            async with session.post(
                "https://cloud.ai-j.jp/demo/aitalk2webapi_nop.php",
                data={"speaker_id": 1209, "text": sentence, "speed": 0.8, "pitch": 1.1},
            ) as resp:
                audio_name = (await resp.text())[47:-3]
            async with session.get(
                f"https://cloud.ai-j.jp/demo/tmp/{audio_name}"
            ) as resp:
                data = await resp.read()
            time = len(data) * 8 / 128000
            start = 3.8 if time > (3.1 if len(sentence) < 4 else 4.5) else 2.3
            if time - start < 0.3:
                return await app.send_message(sender, "有误的文本")
            res = await async_encode(data[int(start * 128000 / 8) :], ios_adaptive=True)
            return await app.send_message(sender, MessageChain(Voice(data_bytes=res)))
        except Exception:
            return await app.send_message(sender, "未知错误")


@alcommand(jp)
@assign("moe")
@exclusive
@accessable
async def tts1(
    app: Ariadne, sender: Sender, jptext: Match[Tuple[str]], char: Match[int]
):
    sentence = " ".join(jptext.result)
    if (id_ := char.result) not in character:
        return await app.send_message(sender, "无效的角色id")
    if id_ > 6:
        id_ -= 7
        speak = "speak2"
    else:
        speak = "speak"
    async with ClientSession(
        connector=TCPConnector(limit=64, verify_ssl=False)
    ) as session:
        try:
            async with session.get(
                f"https://moegoe.azurewebsites.net/api/{speak}?text={sentence}&id={id_}",
                timeout=120,
            ) as resp:
                data = await resp.read()
            if data[:3] == b"400":
                return await app.send_message(sender, "未知错误")
                # print(data)
            res = await async_encode(data, ios_adaptive=True)
            return await app.send_message(sender, MessageChain(Voice(data_bytes=res)))
        except Exception:
            return await app.send_message(sender, "未知错误")
