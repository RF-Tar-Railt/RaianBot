import re
from contextlib import suppress

import diro
from arclet.alconna import Alconna, Args, CommandMeta, Field, namespace
from arclet.alconna.graia import Match, alcommand
from arclet.alconna.tools import MarkdownTextFormatter
from avilla.core import Context
from graia.broadcast.exceptions import PropagationCancelled
from graia.saya.builtins.broadcast.shortcut import priority
from nepattern import BasePattern, MatchMode
from sqlalchemy import select

from app.database import DatabaseService
from app.shortcut import accessable, exclusive, record
from library.dice import coc6, coc6d, coc7, coc7d, dnd, draw, expr, long_insane, rd0, st, temp_insane
from library.dice.constant import help_sc

from .model import CocRule

# fmt: off

with namespace("coc") as np:
    np.headers = [".", "。", "/"]
    np.formatter_type = MarkdownTextFormatter

    name_c = Alconna(
        "name",
        Args["key#名字格式", ["cn", "en", "jp", "enzh"], "$r"]["cnt#名字数量", int, 1],
        meta=CommandMeta(
            "随机名字",
            usage="主要为中文名，日文名和英文名",
            example=".name 5",
            compact=True,
            extra={"supports": {"mirai", "qqapi"}}
        ),
    )

    draw_c = Alconna(
        "draw",
        Args["key#牌堆名称", str, "调查员信息"]["cnt#抽牌数量", int, 1],
        meta=CommandMeta(
            "抽牌",
            usage="牌堆包括塔罗牌，调查员等",
            example=".draw 调查员信息 1",
            compact=True,
            extra={"supports": {"mirai", "qqapi"}}
        ),
    )
    ra_c = Alconna(
        "ra",
        Args["attr#属性名称，如name、名字、str、力量", str, "快速"]["exp", int, -1],
        meta=CommandMeta(
            "快速检定",
            usage="不传入 exp 则不进行结果检定",
            example=".ra str 80",
            compact=True,
            extra={"supports": {"mirai", "qqapi"}}
        ),
    )
    rd_c = Alconna(
        "r",
        Args["pattern#骰子表达式", "re:[^a]+", "1d100"]["exp#期望值", int, -1],
        meta=CommandMeta(
            "投掷指令",
            usage=(
                "d：骰子设定指令\n"
                "#：多轮投掷指令，#后接数字即可设定多轮投掷\n"
                "bp：奖励骰与惩罚骰\n"
            ),
            example=".r1d6",
            compact=True,
            extra={"supports": {"mirai", "qqapi"}}
        ),
    )
    s_or_f = BasePattern(r"\d+(?:d\d+)?\/\d+(?:d\d+)?", model=MatchMode.REGEX_MATCH, alias="suc/fail")
    sc_c = Alconna(
        "sc",
        Args[
            "sf#惩罚值",
            s_or_f,
            Field(
                unmatch_tips=lambda x: "表达式格式错误，应为 '数字/数字' 或 '骰子表达式/骰子表达式'\n比如 '1d10/1d100'",
                missing_tips=lambda: "需要判断表达式。\n可以尝试输入 '/sc 1d10/1d100'"
            )
        ],
        Args["san", int, 80],
        meta=CommandMeta(
            "疯狂检定",
            usage="success：判定成功降低san值，支持x或xdy语法\n"
            "failure：判定失败降低san值，支持语法如上\n"
            "san_number：当前san值，默认为 80",
            example=".sc 1d6/1d6 80",
            extra={"supports": {"mirai", "qqapi"}}
        ),
    )
    st_c = Alconna("st", meta=CommandMeta("射击命中判定", usage="自动掷骰1d20", extra={"supports": {"mirai", "qqapi"}}))
    ti_c = Alconna("ti", meta=CommandMeta("临时疯狂症状", usage="自动掷骰1d10", extra={"supports": {"mirai", "qqapi"}}))
    li_c = Alconna("li", meta=CommandMeta("总结疯狂症状", usage="自动掷骰1d10", extra={"supports": {"mirai", "qqapi"}}))
    dnd_c = Alconna(
        "dnd",
        Args["val#生成数量", int, 1],
        meta=CommandMeta(
            "龙与地下城(DND)人物作成",
            example=".dnd 5",
            compact=True,
            extra={"supports": {"mirai", "qqapi"}}
        ),
    )
    setcoc_c = Alconna(
        "setcoc",
        Args["rule?#coc版本", int],
        meta=CommandMeta(
            "设置房规；不传入参数则为查看当前房规",
            example=".setcoc 2",
            compact=True,
            extra={"supports": {"mirai", "qqapi"}}
        ),
    )
    coc_c = Alconna(
        "coc",
        Args["mode", ["6", "7", "6d", "7d"], Field("7", unmatch_tips=lambda x: "coc后随模式只能为 6，7，6d 和 7d")],
        Args["val#生成数量", int, 1],
        meta=CommandMeta(
            "克苏鲁的呼唤(COC)人物作成, 默认生成7版人物卡",
            usage="接d为详细作成，一次只能作成一个",
            example=".coc6d",
            compact=True,
            extra={"supports": {"mirai", "qqapi"}}
        ),
    )


# fmt: on


@alcommand(name_c, post=True, send_error=True)
@record("coc")
@exclusive
@accessable
async def name_handle(ctx: Context, key: Match[str], cnt: Match[int]):
    if key.result == "$r" or key.result.isdigit():
        return await ctx.scene.send_message(draw("随机姓名", cnt.result))
    return await ctx.scene.send_message(draw(f"随机姓名_{key.result}", cnt.result))


@alcommand(draw_c, post=True, send_error=True)
@record("coc")
@exclusive
@accessable
async def draw_handle(ctx: Context, key: Match[str], cnt: Match[int]):
    return await ctx.scene.send_message(draw(key.result, cnt.result))


@alcommand(ra_c, post=True, send_error=True)
@priority(14)
@record("coc")
@exclusive
@accessable
async def ra_handle(
    ctx: Context,
    attr: Match[str],
    exp: Match[int],
    db: DatabaseService,
):
    async with db.get_session() as session:
        coc_rule = (await session.scalars(select(CocRule).where(CocRule.id == ctx.scene.last_value))).one_or_none()
        rule = coc_rule.rule if coc_rule else 0
    if attr.result.isdigit():
        name = "快速"
        anum = int(attr.result)
    else:
        name = attr.result
        anum = exp.result
        if mat := re.fullmatch(r".+?(\d+)", name):
            anum = int(mat[1])
            name = name[: -len(mat[1])]
        if anum < 0:
            await ctx.scene.send_message(rd0("1d100", None, rule))
            raise PropagationCancelled

    dices = diro.parse("1D100")
    await ctx.scene.send_message(f"{name}检定:\n{expr(dices, anum, rule)}")
    raise PropagationCancelled


@alcommand(rd_c, post=True)
@record("coc")
@exclusive
@accessable
async def rd_handle(
    ctx: Context,
    pattern: Match[str],
    exp: Match[int],
    db: DatabaseService,
):
    """coc骰娘功能"""
    async with db.get_session() as session:
        coc_rule = (await session.scalars(select(CocRule).where(CocRule.id == ctx.scene.last_value))).one_or_none()
        rule = coc_rule.rule if coc_rule else 0
    num = exp.result
    with suppress(ValueError):
        return await ctx.scene.send_message(rd0(pattern.result, num if num >= 0 else None, rule))
    return await ctx.scene.send_message("出错了！")


@alcommand(setcoc_c, post=True, send_error=True)
@record("coc")
@exclusive
@accessable
async def setcoc_handle(
    ctx: Context,
    rule: Match[int],
    db: DatabaseService,
):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return await ctx.scene.send_message("该指令对私聊无效果")
    if not rule.available:
        async with db.get_session() as session:
            coc_rule = (await session.scalars(select(CocRule).where(CocRule.id == ctx.scene.last_value))).one_or_none()
            rule.result = coc_rule.rule if coc_rule else 0
            return await ctx.scene.send_message(f"当前房规为 {rule}")
    if rule.result > 6 or rule.result < 0:
        return await ctx.scene.send_message("规则错误，规则只能为0-6")
    async with db.get_session() as session:
        coc_rule = CocRule(id=ctx.scene.last_value, rule=rule.result)
        await session.merge(coc_rule)
        await session.commit()
        return await ctx.scene.send_message("设置成功")


@alcommand(st_c, post=True, send_error=True)
@record("coc")
@exclusive
@accessable
async def st_handle(ctx: Context):
    return await ctx.scene.send_message(st())


@alcommand(ti_c, post=True, send_error=True)
@record("coc")
@exclusive
@accessable
async def ti_handle(ctx: Context):
    return await ctx.scene.send_message(temp_insane())


@alcommand(li_c, post=True, send_error=True)
@record("coc")
@exclusive
@accessable
async def li_handle(ctx: Context):
    return await ctx.scene.send_message(long_insane())


@alcommand(coc_c, post=True, send_error=True)
@record("coc")
@exclusive
@accessable
async def coc_handle(ctx: Context, val: Match[int], mode: Match[str]):
    if mode.result == "6d":
        return await ctx.scene.send_message(coc6d())
    if mode.result == "7d":
        return await ctx.scene.send_message(coc7d())
    if mode.result == "6":
        return await ctx.scene.send_message(coc6(val.result))
    return await ctx.scene.send_message(coc7(val.result))


@alcommand(dnd_c, post=True, send_error=True)
@record("coc")
@exclusive
@accessable
async def dnd_handle(ctx: Context, val: Match[int]):
    return await ctx.scene.send_message(dnd(val.result))


@alcommand(sc_c, post=True, send_error=True)
@record("coc")
@exclusive
@accessable
async def sc_handle(ctx: Context, sf: Match[str], san: Match[int]):
    try:
        s_and_f = sf.result.split("/")
        success = diro.parse(s_and_f[0])
        success.roll()
        success = success.calc()
        failure = diro.parse(s_and_f[1])
        failure.roll()
        failure = failure.calc()
        r = diro.Dice().roll()()
        s = f"San Check:{r}"
        down = success if r <= san.result else failure
        s += f"理智降低了{down}点"
        if down >= san.result:
            s += "\n该调查员陷入了永久性疯狂"
        elif down >= (san.result // 5):
            s += "\n该调查员陷入了不定性疯狂"
        elif down >= 5:
            s += "\n该调查员陷入了临时性疯狂"
        return await ctx.scene.send_message(s)
    except (IndexError, KeyError, ValueError):
        return await ctx.scene.send_message(help_sc)
