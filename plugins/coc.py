from typing import Tuple
from nepattern import BasePattern, Bind
from arclet.alconna import Alconna, Args, Arparma, CommandMeta, namespace, Empty, ArgFlag, Arg, MultiVar
from arclet.alconna.tools import MarkdownTextFormatter
from arclet.alconna.graia import alcommand, Match, Header
from arclet.alconna.ariadne import AtID
from graia.ariadne.event.lifecycle import ApplicationShutdown
from graiax.shortcut.saya import listen
from graia.broadcast.exceptions import ExecutionStop
from graia.ariadne.model import Group
from graia.ariadne.app import Ariadne
from contextlib import suppress

from app import Sender, RaianBotService, record, Target, exclusive, accessable, send_handler
from library.dice import *

with namespace("coc") as np:
    np.headers = [".", "。"]
    np.formatter_type = MarkdownTextFormatter

    name_c = Alconna(
        "name",
        Args["key#名字格式", ["cn", "en", "jp", "enzh"], "$r"]["cnt#名字数量", int, 1],
        meta=CommandMeta(
            "随机名字",
            example=".name 5"
        )
    )

    draw_c = Alconna(
        "draw",
        Args["key#牌堆名称", str, ""]["cnt#抽牌数量", int, 1],
        meta=CommandMeta(
            "抽牌",
            example=".draw 调查员信息 1",
        )
    )

    rd_c = Alconna(
        "r( )?{dabp}",
        Arg("a_number", int, notice="ra指令使用的数值", flags=[ArgFlag.OPTIONAL]),
        meta=CommandMeta(
            "投掷指令",
            usage="d：骰子设定指令\n"
            "a：检定指令，根据后续a_number设定数值检定\n"
            "#：多轮投掷指令，#后接数字即可设定多轮投掷\n"
            "bp：奖励骰与惩罚骰\n",
            example=".r1d6",
        ),
    )

    rhd_c = Alconna(
        "rh( )?{dabp}",
        Arg("a_number", int, notice="ra指令使用的数值", flags=[ArgFlag.OPTIONAL]),
        meta=CommandMeta(
            "投暗掷指令",
            usage="d：骰子设定指令\n"
            "a：检定指令，根据后续a_number设定数值检定\n"
            "#：多轮投掷指令，#后接数字即可设定多轮投掷\n"
            "bp：奖励骰与惩罚骰；n",
            example=".rha 80",
        ),
    )
    s_or_f = BasePattern(r"\d+(?:d\d+)?\/\d+(?:d\d+)?", alias="suc/fail")
    sc_c = Alconna(
        "sc",
        Args["sf#惩罚值", s_or_f],
        Args["san;?", int],
        meta=CommandMeta(
            "疯狂检定",
            usage="success：判定成功降低san值，支持x或xdy语法\n"
            "failure：判定失败降低san值，支持语法如上\n"
            "san_number：当前san值，缺省san_number将会自动使用保存的人物卡数据",
            example=".sc 1d6/1d6 80",
        ),
    )
    st_c = Alconna("st", meta=CommandMeta("射击命中判定", usage="自动掷骰1d20"))
    ti_c = Alconna("ti", meta=CommandMeta("临时疯狂症状", usage="自动掷骰1d10"))
    li_c = Alconna("li", meta=CommandMeta("总结疯狂症状", usage="自动掷骰1d10"))
    dnd_c = Alconna(
        "dnd",
        Args["val#生成数量", int, 1],
        meta=CommandMeta(
            "龙与地下城(DND)人物作成",
            example=".dnd 5",
        ),
    )
    coc_c = Alconna(
        "coc{num:[6|7]}?{d:d}?",
        Args["val#生成数量", int, 1],
        meta=CommandMeta(
            "克苏鲁的呼唤(COC)人物作成, 默认生成7版人物卡",
            usage="接d为详细作成，一次只能作成一个",
            example=".coc6d",
        ),
    )
    wcoc_c = Alconna(
        "wcoc",
        Args["age;?", int],
        meta=CommandMeta("coc7角色作成并存入角色卡", example=".wcoc 16")
    )
    en_c = Alconna(
        "en",
        Args["skill_level#需要成长的技能当前等级", int],
        meta=CommandMeta("技能成长", example=".en 5"),
    )
    set_c = Alconna(
        "set",
        Args["name#属性名称，如name、名字、str、力量", str, Empty]["val;?#属性值", str],
        meta=CommandMeta(
            "角色卡设定", usage="可以单独输入set指令，将自动读取最近一次coc指令结果进行保存", example=".set name HEH"
        ),
    )
    show_c = Alconna(
        "show",
        Args["uid;?", AtID],
        meta=CommandMeta("查看指定调查员保存的人物卡", usage="不传入 uid 则查询自身人物卡"),
    )
    shows_c = Alconna(
        "shows",
        Args["uid;?", AtID],
        meta=CommandMeta("查看指定调查员的技能表", usage="不传入 uid 则查询自身技能表"),
    )
    ra_c = Alconna(
        "ra",
        Args["attr#属性名称，如name、名字、str、力量", str]["exp", int, -1],
        meta=CommandMeta("快速检定")
    )
    del_c = Alconna(
        "del",
        Args["data", MultiVar(Bind[str, "c|card|xxx"], "+")],
        meta=CommandMeta(
            "删除数据",
            usage="data可以有以下值\n"
            "c:清空暂存数据\n"
            "card:删除使用中的人物卡(慎用)\n"
            "xxx:其他任意技能名",
            example=".del c card"
        )
    )

bot = RaianBotService.current()
card = Cards(f"{bot.config.plugin_cache_dir / 'coc_cards.json' }")
card.load()

@alcommand(name_c)
@record("coc")
@exclusive
@accessable
async def name_handle(app: Ariadne, sender: Sender, key: Match[str], cnt: Match[int]):
    if key.result == "$r" or key.result.isdigit():
        return await app.send_message(sender, draw("随机姓名", cnt.result))
    return await app.send_message(sender, draw(f"随机姓名_{key.result}", cnt.result))

@alcommand(draw_c)
@record("coc")
@exclusive
@accessable
async def draw_handle(app: Ariadne, sender: Sender, key: Match[str], cnt: Match[int]):
    if not key.result:
        return await app.send_message(sender, await send_handler(draw_c.get_help()))
    await app.send_message(sender, draw(key.result, cnt.result))

@alcommand(ra_c)
@record("coc")
@exclusive
@accessable
async def ra_handle(app: Ariadne, sender: Sender, target: Target, attr: Match[str], exp: Match[int]):
    if attr.result.isdigit():
        return
    if isinstance(sender, Group):
        res = card.ra_handler(attr.result.lower(), exp.result, f"{app.account}_g{sender.id}", target.id)
    else:
        res = card.ra_handler(attr.result.lower(), exp.result, f"{app.account}_g{sender.id}")
    await app.send_message(sender, res)
    raise ExecutionStop


@alcommand(rd_c)
@record("coc")
@exclusive
@accessable
async def rd_handle(
    app: Ariadne, sender: Sender,
    result: Arparma, a_number: Match[int]
):
    """coc骰娘功能"""
    pat = result.header["dabp"]
    if "h" in pat:
        return
    if pat.strip() == "a":
        pat = "1d100"
    with suppress(ValueError):
        return await app.send_message(sender, rd0(pat, a_number.result if a_number.available else None))
    return await app.send_message(sender, "出错了！")


@alcommand(rhd_c, private=False)
@record("coc")
@exclusive
@accessable
async def rhd_handle(
    app: Ariadne, sender: Sender, target: Target,
    result: Arparma, a_number: Match[int]
):
    if not app.get_friend(target.id):
        return await app.send_message(sender, "请先加bot 为好友")
    pat = result.header["dabp"]
    with suppress(ValueError):
        return await app.send_friend_message(target.id, rd0(pat, a_number.result if a_number.available else None))
    return await app.send_friend_message(target.id, "出错了！")


@alcommand(st_c)
@record("coc")
@exclusive
@accessable
async def st_handle(app: Ariadne, sender: Sender):
    return await app.send_message(sender, st())


@alcommand(ti_c)
@record("coc")
@exclusive
@accessable
async def ti_handle(app: Ariadne, sender: Sender):
    return await app.send_message(sender, temp_insane())


@alcommand(li_c)
@record("coc")
@exclusive
@accessable
async def li_handle(app: Ariadne, sender: Sender):
    return await app.send_message(sender, long_insane())


@alcommand(en_c)
@record("coc")
@exclusive
@accessable
async def en_handle(app: Ariadne, sender: Sender, skill_level: Match[int]):
    return await app.send_message(sender, en(skill_level.result))

@alcommand(coc_c)
@record("coc")
@exclusive
@accessable
async def coc_handle(app: Ariadne, sender: Sender, val: Match[int], header: Header):
    if header.result.get("d"):
        if header.result.get("num") == "6":
            return await app.send_message(sender, coc6d())
        return await app.send_message(sender, coc7d())
    if header.result.get("num") == "6":
        return await app.send_message(sender, coc6(val.result))
    return await app.send_message(sender, coc7(val.result))


@alcommand(dnd_c)
@record("coc")
@exclusive
@accessable
async def dnd_handle(app: Ariadne, sender: Sender, val: Match[int]):
    return await app.send_message(sender, dnd(val.result))


@alcommand(wcoc_c)
@record("coc")
@exclusive
@accessable
async def wcoc_handle(app: Ariadne, sender: Sender, target: Target, age: Match[int]):
    arg = age.result if age.available else 20
    inv = Investigator()
    await app.send_message(sender, inv.age_change(arg))
    if 15 <= arg <= 90:
        if isinstance(sender, Group):
            card.cache_update(inv.dump(), f"{app.account}_g{sender.id}", target.id)
        else:
            card.cache_update(inv.dump(), f"f{app.account}_{sender.id}")
        await app.send_message(sender, inv.output())


@alcommand(sc_c)
@record("coc")
@exclusive
@accessable
async def sc_handle(app: Ariadne, sender: Sender, target: Target, sf: Match[str], san: Match[int]):
    if isinstance(sender, Group):
        res = card.sc_handler(sf.result.lower(), san.result if san.available else None, f"{app.account}_g{sender.id}", target.id)
    else:
        res = card.sc_handler(sf.result.lower(), san.result if san.available else None, f"{app.account}_f{sender.id}")
    return await app.send_message(sender, res)


@alcommand(set_c)
@record("coc")
@exclusive
@accessable
async def set_handle(app: Ariadne, sender: Sender, target: Target, result: Arparma):
    if isinstance(sender, Group):
        res = card.set_handler(
            result.all_matched_args.get("name"),
            result.all_matched_args.get("val"),
            f"{app.account}_g{sender.id}", target.id
        )
    else:
        res = card.set_handler(
            result.all_matched_args.get("name"),
            result.all_matched_args.get("val"),
            f"{app.account}_f{sender.id}"
        )
    return await app.send_message(sender, res)


@alcommand(show_c)
@record("coc")
@exclusive
@accessable
async def show_handle(app: Ariadne, sender: Sender, target: Target, uid: Match[int]):
    if isinstance(sender, Group):
        res = card.show_handler(f"{app.account}_g{sender.id}", uid.result if uid.available else target.id)
    else:
        res = card.show_handler(f"{app.account}_f{sender.id}")
    return await app.send_message(sender, '\n'.join(res))


@alcommand(shows_c)
@record("coc")
@exclusive
@accessable
async def shows_handle(app: Ariadne, sender: Sender, target: Target, uid: Match[int]):
    if isinstance(sender, Group):
        res = card.show_skill_handler(f"{app.account}_g{sender.id}", uid.result if uid.available else target.id)
    else:
        res = card.show_skill_handler(f"{app.account}_f{sender.id}")
    return await app.send_message(sender, res)


@alcommand(del_c)
@record("coc")
@exclusive
@accessable
async def del_handle(app: Ariadne, sender: Sender, target: Target, data: Match[Tuple[str]]):
    if isinstance(sender, Group):
        res = card.del_handler([i.lower() for i in data.result], f"{app.account}_g{sender.id}", target.id)
    else:
        res = card.del_handler([i.lower() for i in data.result], f"{app.account}_f{sender.id}")
    return await app.send_message(sender, "\n".join(res))


@listen(ApplicationShutdown)
async def _save():
    card.save()
