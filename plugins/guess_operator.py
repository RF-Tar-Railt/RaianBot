from contextlib import suppress
from pathlib import Path
from typing import Tuple, Union

from app import RaianBotInterface, Sender, record
from arclet.alconna import Args, CommandMeta, Option
from arclet.alconna.graia import Alconna, Match, alcommand, assign
from arknights_toolkit.wordle import Guess, OperatorWordle, update
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.model import Friend, Group
from graia.ariadne.util.interrupt import FunctionWaiter

alc = Alconna(
    "猜干员",
    Args["max_guess", int, 8],
    Args["simple;K", bool, False],
    Option("更新", Args["name;S", str]),
    Option("提示"),
    Option("重置"),
    meta=CommandMeta("明日方舟猜干员游戏", usage="可以指定最大猜测次数"),
)


@alcommand(alc)
@record("猜干员")
@assign("提示")
async def guess_info(app: Ariadne, sender: Sender):
    image = Path("assets/image/guess.png").open("rb").read()
    return await app.send_message(sender, MessageChain(Image(data_bytes=image)))


@alcommand(alc)
@record("猜干员")
@assign("更新")
async def guess_update(app: Ariadne, sender: Sender, name: Match[Tuple[str, ...]]):
    update(*name.result)
    return await app.send_message(sender, "更新完毕")


@alcommand(alc)
@record("猜干员")
@assign("重置")
async def guess_reset(
        app: Ariadne,
        sender: Sender,
        bot: RaianBotInterface,
):
    if (path := Path(f"{bot.config.cache_dir}/plugins/guess")).exists():
        for file in path.iterdir():
            file.unlink(missing_ok=True)
    return await app.send_message(sender, "重置完毕")


@alcommand(alc)
@record("猜干员")
@assign("$main")
async def guess(
        app: Ariadne,
        sender: Sender,
        bot: RaianBotInterface,
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
            waiter,
            [GroupMessage, FriendMessage],
            block_propagation=isinstance(sender, Friend),
        ).wait(timeout=120, default=False)
        if res is None:
            continue
        if not res:
            wordle.restart(id_)
            return await app.send_message(
                sender,
                f"{'' if isinstance(sender, Friend) else f'{sender.name}的'}游戏已结束！",
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
        f"{'' if isinstance(sender, Friend) else f'{sender.name}的'}游戏已结束！\n答案为{res.select}",
    )
