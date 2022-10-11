from typing import Tuple, Union
from pathlib import Path
from contextlib import suppress
from arclet.alconna import CommandMeta, Args, Option
from arclet.alconna.graia import Alconna, alcommand, Match, assign
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.util.interrupt import FunctionWaiter
from graia.ariadne.model import Friend, Group
from graia.ariadne.app import Ariadne
from app import Sender, record, RaianMain
from arknights_toolkit.wordle import OperatorWordle, update, Guess

alc = Alconna(
    "猜干员",
    Args["max_guess", int, 8],
    Args["simple;K", bool, False],
    Option("更新", Args["name;S", str]),
    Option("提示"),
    Option("重置"),
    meta=CommandMeta("明日方舟猜干员游戏", usage="可以指定最大猜测次数"),
)


@record("猜干员")
@assign("提示")
@alcommand(alc)
async def guess(app: Ariadne, sender: Sender):
    image = Path("assets/image/guess.png").open("rb").read()
    return await app.send_message(sender, MessageChain(Image(data_bytes=image)))


@record("猜干员")
@assign("更新")
@alcommand(alc)
async def guess(app: Ariadne, sender: Sender, name: Match[Tuple[str, ...]]):
    update(*name.result)
    return await app.send_message(sender, "更新完毕")


@record("猜干员")
@assign("重置")
@alcommand(alc)
async def guess(
    app: Ariadne,
    sender: Sender,
    bot: RaianMain,
):
    if (path := Path(f"{bot.config.cache_dir}/plugins/guess")).exists():
        for file in path.iterdir():
            file.unlink(missing_ok=True)
    return await app.send_message(sender, "重置完毕")


@record("猜干员")
@assign("$main")
@alcommand(alc)
async def guess(
    app: Ariadne,
    sender: Sender,
    bot: RaianMain,
    max_guess: Match[int],
    simple: Match[bool],
):
    id_ = f"g{sender.id}" if isinstance(sender, Group) else f"f{sender.id}"
    if (Path(f"{bot.config.cache_dir}/plugins/guess") / f"{id_}.json").exists():
        return await app.send_message(sender, "当前已有游戏运行！")
    wordle = OperatorWordle(f"{bot.config.cache_dir}/plugins/guess", max_guess.result)
    wordle.select(id_)
    await app.send_message(sender, "猜干员游戏开始！\n发送 取消 可以结束当前游戏")

    async def waiter(waiter_sender: Sender, message: MessageChain):
        name = str(message)
        if sender.id == waiter_sender.id:
            if name.startswith("取消"):
                await app.send_message(sender, "已取消")
                return False
            with suppress(ValueError):
                return wordle.guess(name, id_)
            return

    while True:
        res: Union[bool, Guess, None] = await FunctionWaiter(
            waiter, [GroupMessage, FriendMessage]
        ).wait(timeout=120, default=False)
        if res is None:
            continue
        if not res:
            wordle.restart(id_)
            return await app.send_message(
                sender, f"{'' if isinstance(sender, Friend) else f'{sender.name}的'}游戏已结束！"
            )
        if simple.result:
            await app.send_message(sender, MessageChain(wordle.draw(res, simple=True)))
        else:
            await app.send_message(
                sender, MessageChain(Image(data_bytes=wordle.draw(res)))
            )
        if res.state != "guessing":
            break
    return await app.send_message(
        sender,
        f"{'' if isinstance(sender, Friend) else f'{sender.name}的'}游戏已结束！\n答案为{res.select}"
    )