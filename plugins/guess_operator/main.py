from contextlib import suppress
from pathlib import Path
from secrets import token_hex
from typing import Union

from arclet.alconna import Alconna, Args, CommandMeta, Kw, Option
from arclet.alconna.graia import Match, alcommand, assign
from arknights_toolkit.wordle import Guess, OperatorWordle
from avilla.core import Context, MessageChain, MessageReceived, Notice, Picture, RawResource
from avilla.core.exceptions import ActionFailed

from app.core import RaianBotService
from app.interrupt import FunctionWaiter
from app.shortcut import accessable, exclusive, picture, record

alc = Alconna(
    "猜干员",
    Args["max_guess", int, 8],
    Args["simple", Kw @ bool, False],
    Option("更新", help_text="更新干员列表"),
    Option("规则", help_text="获取游戏规则"),
    Option("重置", help_text="重置游戏"),
    meta=CommandMeta("明日方舟猜干员游戏", usage="可以指定最大猜测次数", extra={"supports": {"mirai", "qqapi"}}),
)

bot = RaianBotService.current()
wordle = OperatorWordle(f"{bot.config.plugin_data_dir / 'guess'}")


@alcommand(alc, post=True, send_error=True)
@record("猜干员")
@assign("规则")
@exclusive
@accessable
async def guess_info(ctx: Context):
    img = Path("assets/image/guess.png").read_bytes()
    try:
        return await ctx.scene.send_message(Picture(RawResource(img)))
    except Exception:
        url = await bot.upload_to_cos(img, f"guess_rule_{token_hex(16)}.jpg")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            text = """\
绿脸点赞：猜测的干员该属性和神秘干员完全一样!太棒了!
红脸摇手：猜测的干员该属性和神秘千员完全不一样!难搞哦!
蓝脸指下：猜测的千员稀有度比神秘干员高!试着往低星猜吧!
蓝脸指上：猜测的千员稀有度比神秘千员低!试着往高星猜吧!
黄连疑惑：猜测的干员该属性和神秘千员部分一样!再加把劲!
千员所属的阵营拆成了多级维度
和出身地无关，请查阅关系网!
职业也区分了主职业和分支职业!
点击干员姓名可以看到详情!
游戏数据来自PRTS!"""
            return await ctx.scene.send_message(text)


@alcommand(alc, post=True, send_error=True)
@record("猜干员")
@assign("更新")
@exclusive
@accessable
async def guess_update(ctx: Context):
    await wordle.update(bot.config.proxy)
    return await ctx.scene.send_message("更新完毕")


@alcommand(alc, post=True, send_error=True)
@record("猜干员")
@assign("重置")
@exclusive
@accessable
async def guess_reset(ctx: Context):
    session = "_".join(ctx.scene.pattern.values())
    if (file := Path(f"{bot.config.plugin_data_dir / 'guess' / f'{session}.json'}")).exists():
        file.unlink(missing_ok=True)
    return await ctx.scene.send_message("重置完毕")


@alcommand(alc, post=True, send_error=True)
@record("猜干员")
@assign("$main")
@exclusive
@accessable
async def guess(
    ctx: Context,
    max_guess: Match[int],
    simple: Match[bool],
):
    session = "_".join(ctx.scene.pattern.values())

    if (Path(f"{bot.config.plugin_data_dir / 'guess' / f'{session}.json'}")).exists():
        if session not in bot.cache.setdefault("$guess", []):
            return await ctx.scene.send_message(
                f"游戏异常，请重置后再试\n重置方法：{bot.config.command.headers[0]}猜干员 重置",
            )
        await ctx.scene.send_message("游戏继续！")
        return
    else:
        wordle.select(session)
        await ctx.scene.send_message(
            "猜干员游戏开始！\n" "请尽量用回复bot的形式发送干员名字\n" "发送 取消 或 @bot 取消 可以结束当前游戏",
        )

    async def waiter(waiter_ctx: Context, message: MessageChain):
        name = str(message.exclude(Notice)).lstrip()
        if waiter_ctx.scene.pattern == ctx.scene.pattern:
            if name.startswith("取消"):
                await waiter_ctx.scene.send_message("已取消")
                return False
            with suppress(ValueError):
                return wordle.guess(name, session, max_guess.result)
            return

    bot.cache.setdefault("$guess", []).append(session)
    while True:
        res: Union[bool, Guess, None] = await FunctionWaiter(
            waiter,
            [MessageReceived],
            block_propagation=ctx.client.follows("::friend") or ctx.client.follows("::guild.user"),
        ).wait(timeout=120, default=False)
        if res is None:
            continue
        if not res:
            ans = wordle.restart(session)
            bot.cache["$guess"].remove(session)
            return await ctx.scene.send_message("游戏已结束！" + (f"\n答案为{ans.select}" if ans else ""))
        try:
            if simple.result:
                await ctx.scene.send_message(wordle.draw(res, simple=True, max_guess=max_guess.result))
            else:
                img = wordle.draw(res, max_guess=max_guess.result)
                try:
                    await ctx.scene.send_message(Picture(RawResource(img)))
                except Exception:
                    url = await bot.upload_to_cos(img, f"guess_{token_hex(16)}.jpg")
                    try:
                        await ctx.scene.send_message(picture(url, ctx))
                    except ActionFailed:
                        await ctx.scene.send_message(wordle.draw(res, simple=True, max_guess=max_guess.result))
        except Exception as e:
            await ctx.scene.send_message(f"{e}")
            break
        if res.state != "guessing":
            break
    wordle.restart(session)
    bot.cache["$guess"].remove(session)
    answer = (
        f"{res.select}\n"
        f"星数：{'★' * (res.data['rarity'] + 1 )}\n"
        f"职业：{res.data['career']}\n"
        f"种族：{res.data['race']}\n"
        f"阵营：{res.data['org']}\n"
        f"画师：{res.data['artist']}\n"
    )
    return await ctx.scene.send_message(f"游戏已结束！\n答案为{answer}")
