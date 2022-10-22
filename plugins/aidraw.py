import time
from base64 import b64encode
from typing import Tuple

from app import RaianMain, Sender, Target, record
from arclet.alconna import Args, CommandMeta, Option, store_value
from arclet.alconna.graia import Alconna, Match, Query, alcommand
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, Source
from graia.ariadne.model import Group
from graia.ariadne.util.interrupt import FunctionWaiter
from httpx import AsyncClient
from modules.aiml.lang_support import is_include_chinese
from modules.translate import YoudaoTrans

running = set()
r18tag = ["pussy", "vagina", "sex", "penis", "exposed", "carcass", "breathless"]


async def _handle(prompt: Tuple[str, ...], r18: bool):
    trans = YoudaoTrans()
    negative_prompt = [
        "nsfw",
        "lowres",
        "bad anatomy",
        "bad hands",
        "text",
        "error",
        "missing fingers",
        "extra digit",
        "fewer digits",
        "cropped",
        "worst quality",
        "low quality",
        "normal quality",
        "jpeg artifacts",
        "signature",
        "watermark",
        "username",
        "blurry",
        "text font ui",
        "malformed hands",
        "long neck",
        "missing limb",
        "Sleeveles",
        "bad anatomy disfigured malformed mutated",
        "(mutated hands and fingers :1.5)",
        "(long body :1.3)",
        "bad anatomy disfigured malformed mutated",
        "multiple breasts",
        "badfeet",
        "futa",
        "yaoi",
    ]
    tags = list(prompt)
    for i in range(len(tags)):
        if "-" in tags[i]:
            tags[i] = tags[i].replace("-", " ")
        if is_include_chinese(prompt[i]):
            tags[i] = await trans.trans(tags[i], "en")
    if not r18:
        negative_prompt.extend(r18tag)
        for i in tags.copy():
            if i in r18tag:
                tags.remove(i)
    return tags, negative_prompt


@record("ai绘画")
@alcommand(
    Alconna(
        "作画",
        Args["prompt;S", str],
        Option("-sd|--seed", Args["seed", int]),
        Option("-st|--step", Args["step", int]),
        Option("-W|--width", Args["width", [512, 768]]),
        Option("-H|--height", Args["height", [512, 1280]]),
        Option("-C|--scale", Args["scale", float]),
        Option("-r18", action=store_value(True)),
        meta=CommandMeta(
            "以关键词为基础进行AI作画, 关键词用空格分割",
            usage="同一时间只能有一次运行任务",
            example="$作画 girl white-hair",
        ),
    )
)
async def draw(
    app: Ariadne,
    sender: Sender,
    source: Source,
    bot: RaianMain,
    prompt: Match[Tuple[str, ...]],
    seed: Query[int] = Query("seed.seed", -1),
    step: Query[int] = Query("step.step", 32),
    scale: Query[float] = Query("scale.scale", 7.0),
    width: Query[int] = Query("width.width", 512),
    height: Query[int] = Query("height.height", 512),
    r18: Query[bool] = Query("r18.value", False),
):
    """ai作画功能"""
    id_ = f"g{sender.id}" if isinstance(sender, Group) else f"f{sender.id}"
    if running:
        if id_ in running:
            return await app.send_message(sender, "正在作画中，别着急~", quote=source)
        return await app.send_message(sender, "存在其他群组的作画任务，请耐心排队等候", quote=source)
    running.add(id_)
    prompt, negative_prompt = await _handle(prompt.result, r18.result)
    req = {
        "prompt": ",".join(
            [
                "masterpiece",
                "extremely detailed CG unity 8k wallpaper",
                "best quality",
                "highres",
                "original",
            ]
            + prompt
        ),
        "negative_prompt": ",".join(negative_prompt),
        "seed": seed.result,
        "steps": step.result,
        "height": height.result,
        "width": width.result,
        "cfg_scale": scale.result,
    }
    header = {"Content-type": "application/json", "accept": "application/json"}
    try:
        async with AsyncClient(headers=header) as client:
            st = time.time()
            resp = await client.post(
                bot.config.plugin["txt2img"],
                json={"txt2imgreq": req},
                timeout=200,
            )
            data = resp.json()
            ed = time.time()
            await app.send_message(
                sender,
                MessageChain(
                    f"cost: {ed - st:.2f} s\n",
                    f"seed: {data['seed']}\n",
                    Image(base64=data["images"][0]),
                ),
            )
    finally:
        running.clear()


@record("ai绘画")
@alcommand(
    Alconna(
        "图画",
        Args["prompt;S", str],
        Args["img;O", Image],
        Option("-sd", Args["seed", int]),
        Option("-r18", action=store_value(True)),
        meta=CommandMeta("用传入图片为基础进行AI作画, 关键词用空格分割", usage="同一时间只能有一次运行任务"),
    )
)
async def draw(
    app: Ariadne,
    sender: Sender,
    source: Source,
    target: Target,
    bot: RaianMain,
    img: Match[Image],
    prompt: Match[Tuple[str, ...]],
    seed: Query[int] = Query("sd.seed", -1),
    r18: Query[bool] = Query("r18.value", False),
):
    """ai作画功能"""

    async def wait_img(message: MessageChain, wait_sender: Sender, wait_target: Target):
        if wait_sender.id == sender.id and wait_target.id == target.id:
            waiter1_saying = message.display
            if waiter1_saying == "取消":
                return
            if message.has(Image):
                return message.get_first(Image)
            else:
                await app.send_message(sender, MessageChain("请发送图片"))
                return False

    if not img.available:
        res = await FunctionWaiter(wait_img, [FriendMessage, GroupMessage]).wait(
            timeout=20
        )
        if res is None:
            return await app.send_message(sender, "已取消作图任务")
        if not res:
            return
        image = res
    else:
        image = img.result
    id_ = f"g{sender.id}" if isinstance(sender, Group) else f"f{sender.id}"
    if running:
        if id_ in running:
            return await app.send_message(sender, "正在作画中，别着急~", quote=source)
        return await app.send_message(sender, "存在其他群组的作画任务，请耐心排队等候", quote=source)
    running.add(id_)
    prompt, negative_prompt = await _handle(prompt.result, r18.result)
    img_b64 = b64encode(await image.get_bytes()).decode("utf-8")
    req = {
        "prompt": ",".join(
            [
                "masterpiece",
                "extremely detailed CG unity 8k wallpaper",
                "best quality",
                "highres",
                "original",
            ]
            + prompt
        ),
        "negative_prompt": ",".join(negative_prompt),
        "init_img": img_b64,
        "seed": seed.result,
    }
    header = {"Content-type": "application/json", "accept": "application/json"}
    try:
        async with AsyncClient(headers=header) as client:
            resp = await client.post(
                bot.config.plugin["img2img"], json={"img2imgreq": req}
            )
            data = resp.json()
            await app.send_message(
                sender,
                MessageChain(f"seed: {data['seed']}", Image(base64=data["images"][0])),
            )
    finally:
        running.clear()
