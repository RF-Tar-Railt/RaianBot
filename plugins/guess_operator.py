from contextlib import suppress
from pathlib import Path
from typing import Union

from app import Sender, record, accessable, exclusive, RaianBotService, RaianBotInterface
from arclet.alconna import Alconna, Args, CommandMeta, Option, Kw
from arclet.alconna.graia import Match, alcommand, assign
from arknights_toolkit.wordle import Guess, OperatorWordle
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.model import Friend, Group
from graia.ariadne.util.interrupt import FunctionWaiter

alc = Alconna(
    "猜干员",
    Args["max_guess", int, 8],
    Args["simple", Kw @ bool, False],
    Option("更新"),
    Option("规则"),
    Option("重置"),
    meta=CommandMeta("明日方舟猜干员游戏", usage="可以指定最大猜测次数"),
)

bot = RaianBotService.current()
wordle = OperatorWordle(f"{bot.config.plugin_cache_dir / 'guess'}")

@alcommand(alc)
@record("猜干员")
@assign("规则")
@exclusive
@accessable
async def guess_info(app: Ariadne, sender: Sender):
    image = Path("assets/image/guess.png").open("rb").read()
    return await app.send_message(sender, MessageChain(Image(data_bytes=image)))


@alcommand(alc)
@record("猜干员")
@assign("更新")
@exclusive
@accessable
async def guess_update(app: Ariadne, sender: Sender):
    await wordle.update()
    return await app.send_message(sender, "更新完毕")


@alcommand(alc)
@record("猜干员")
@assign("重置")
@exclusive
@accessable
async def guess_reset(app: Ariadne, sender: Sender):
    id_ = f"{app.account}_g{sender.id}" if isinstance(sender, Group) else f"{app.account}_f{sender.id}"
    if (file := Path(f"{bot.config.plugin_cache_dir / 'guess' / f'{id_}.json'}")).exists():
        file.unlink(missing_ok=True)
    return await app.send_message(sender, "重置完毕")


@alcommand(alc)
@record("猜干员")
@assign("$main")
@exclusive
@accessable
async def guess(
    app: Ariadne,
    sender: Sender,
    max_guess: Match[int],
    simple: Match[bool],
    current_bot: RaianBotInterface,
):
    id_ = f"g{sender.id}" if isinstance(sender, Group) else f"f{sender.id}"

    if (Path(f"{bot.config.plugin_cache_dir / 'guess' / f'{id_}.json'}")).exists():
        if id_ not in current_bot.data.cache.setdefault("$guess", []):
            return await app.send_message(sender, f"游戏异常，请重置后再试\n重置方法：{bot.config.command.headers[0]}猜干员 重置")
        await app.send_message(sender, "游戏继续！")
    else:
        wordle.select(id_)
        await app.send_message(sender, "猜干员游戏开始！\n发送 取消 可以结束当前游戏")

    async def waiter(waiter_sender: Sender, message: MessageChain):
        name = str(message)
        if sender.id == waiter_sender.id:
            if name.startswith("取消"):
                await app.send_message(sender, "已取消")
                return False
            with suppress(ValueError):
                return wordle.guess(name, id_, max_guess.result)
            return
    current_bot.data.cache.setdefault("$guess", []).append(id_)
    while True:
        res: Union[bool, Guess, None] = await FunctionWaiter(
            waiter,
            [GroupMessage, FriendMessage],
            block_propagation=isinstance(sender, Friend),
        ).wait(timeout=120, default=False)
        if res is None:
            continue
        if not res:
            ans = wordle.restart(id_)
            current_bot.data.cache["$guess"].remove(id_)
            return await app.send_message(
                sender,
                f"{'' if isinstance(sender, Friend) else f'{sender.name}的'}游戏已结束！\n答案为{ans.select}",
            )
        try:
            if simple.result:
                await app.send_message(sender, MessageChain(wordle.draw(res, simple=True, max_guess=max_guess.result)))
            else:
                await app.send_message(sender, MessageChain(Image(data_bytes=wordle.draw(res, max_guess=max_guess.result))))
        except Exception as e:
            await app.send_friend_message(current_bot.config.admin.master_id, f'{e}')
            break
        if res.state != "guessing":
            break
    wordle.restart(id_)
    current_bot.data.cache["$guess"].remove(id_)
    answer = (
        f"{res.select}\n"
        f"星数：{'★' * (res.data['rarity'] + 1 )}\n"
        f"职业：{res.data['career']}\n"
        f"种族：{res.data['race']}\n"
        f"阵营：{res.data['org']}\n"
        f"画师：{res.data['artist']}\n"
    )
    return await app.send_message(
        sender,
        f"{'' if isinstance(sender, Friend) else f'{sender.name}的'}游戏已结束！\n答案为{answer}",
    )
