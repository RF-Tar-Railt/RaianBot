from typing import Tuple
from nepattern import BasePattern, Bind
from arclet.alconna import Args, Arpamar, CommandMeta, namespace, Empty
from arclet.alconna.graia import Alconna, alcommand, AtID, Match
from graia.ariadne.event.lifecycle import ApplicationShutdown
from graia.ariadne.util.saya import listen
from graia.ariadne.model import Group
from graia.ariadne.app import Ariadne
from contextlib import suppress

from app import Sender, RaianMain, record, Target
from modules.dice import *

with namespace("coc") as np:
    np.headers = [".", "。"]

    rd_c = Alconna(
        "r( )?{dabp}",
        Args["a_number;O#ra指令使用的数值", int],
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
        Args["a_number;O#ra指令使用的数值", int],
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
        Args["san;O", int],
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
    coc_c = Alconna(
        "coc",
        Args["val;O", int],
        meta=CommandMeta("coc角色作成", example=".coc 20")
    )
    en_c = Alconna(
        "en",
        Args["skill_level#需要成长的技能当前等级", int],
        meta=CommandMeta("技能成长", example=".en 5"),
    )
    set_c = Alconna(
        "set",
        Args["name#属性名称，如name、名字、str、力量", str, Empty]["val;O#属性值", str],
        meta=CommandMeta(
            "角色卡设定", usage="可以单独输入set指令，将自动读取最近一次coc指令结果进行保存", example=".set name HEH"
        ),
    )
    show_c = Alconna(
        "show",
        Args["uid;O", AtID],
        meta=CommandMeta("查看指定调查员保存的人物卡", usage="不传入 uid 则查询自身人物卡"),
    )
    shows_c = Alconna(
        "shows",
        Args["uid;O", AtID],
        meta=CommandMeta("查看指定调查员的技能表", usage="不传入 uid 则查询自身技能表"),
    )
    sa_c = Alconna(
        "sa",
        Args["name#属性名称，如name、名字、str、力量", str],
        meta=CommandMeta("快速检定")
    )
    del_c = Alconna(
        "del",
        Args["data;S", Bind[str, "c|card|xxx"]],
        meta=CommandMeta(
            "删除数据",
            usage="data可以有以下值\n"
            "c:清空暂存数据\n"
            "card:删除使用中的人物卡(慎用)\n"
            "xxx:其他任意技能名",
            example=".del c card"
        )
    )

bot = RaianMain.current()
cards = Cards(f"{bot.config.cache_dir}/plugins/coc_cards.json")
cards.load()


@record("coc")
@alcommand(rd_c)
async def rd_handle(
    app: Ariadne, sender: Sender,
    result: Arpamar, a_number: Match[int]
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


@record("coc")
@alcommand(rhd_c, private=False)
async def rhd_handle(
    app: Ariadne, sender: Sender, target: Target,
    result: Arpamar, a_number: Match[int]
):
    if not app.get_friend(target.id):
        return await app.send_message(sender, "请先加bot 为好友")
    pat = result.header["dabp"]
    with suppress(ValueError):
        return await app.send_friend_message(target.id, rd0(pat, a_number.result if a_number.available else None))
    return await app.send_friend_message(target.id, "出错了！")


@record("coc")
@alcommand(st_c)
async def st_handle(app: Ariadne, sender: Sender):
    return await app.send_message(sender, st())


@record("coc")
@alcommand(ti_c)
async def ti_handle(app: Ariadne, sender: Sender):
    return await app.send_message(sender, ti())


@record("coc")
@alcommand(li_c)
async def li_handle(app: Ariadne, sender: Sender):
    return await app.send_message(sender, li())


@record("coc")
@alcommand(en_c)
async def en_handle(app: Ariadne, sender: Sender, skill_level: Match[int]):
    return await app.send_message(sender, en(skill_level.result))


@record("coc")
@alcommand(coc_c)
async def coc_handle(app: Ariadne, sender: Sender, target: Target, val: Match[int]):
    arg = val.result if val.available else 20
    inv = Investigator()
    await app.send_message(sender, inv.age_change(arg))
    if 15 <= arg <= 90:
        if isinstance(sender, Group):
            cards.cache_update(inv.dump(), f"g{sender.id}", target.id)
        else:
            cards.cache_update(inv.dump(), f"f{sender.id}")
        await app.send_message(sender, inv.output())


@record("coc")
@alcommand(sc_c)
async def sc_handle(app: Ariadne, sender: Sender, target: Target, sf: Match[str], san: Match[int]):
    if isinstance(sender, Group):
        res = cards.sc_handler(sf.result.lower(), san.result if san.available else None, f"g{sender.id}", target.id)
    else:
        res = cards.sc_handler(sf.result.lower(), san.result if san.available else None, f"f{sender.id}")
    return await app.send_message(sender, res)


@record("coc")
@alcommand(set_c)
async def set_handle(app: Ariadne, sender: Sender, target: Target, result: Arpamar):
    if isinstance(sender, Group):
        res = cards.set_handler(
            result.all_matched_args.get("name"),
            result.all_matched_args.get("val"),
            f"g{sender.id}", target.id
        )
    else:
        res = cards.set_handler(
            result.all_matched_args.get("name"),
            result.all_matched_args.get("val"),
            f"f{sender.id}"
        )
    return await app.send_message(sender, res)


@record("coc")
@alcommand(show_c)
async def show_handle(app: Ariadne, sender: Sender, target: Target, uid: Match[int]):
    if isinstance(sender, Group):
        res = cards.show_handler(f"g{sender.id}", uid.result if uid.available else target.id)
    else:
        res = cards.show_handler(f"f{sender.id}")
    return await app.send_message(sender, '\n'.join(res))


@record("coc")
@alcommand(shows_c)
async def shows_handle(app: Ariadne, sender: Sender, target: Target, uid: Match[int]):
    if isinstance(sender, Group):
        res = cards.show_skill_handler(f"g{sender.id}", uid.result if uid.available else target.id)
    else:
        res = cards.show_skill_handler(f"f{sender.id}")
    return await app.send_message(sender, res)


@record("coc")
@alcommand(sa_c)
async def sa_handle(app: Ariadne, sender: Sender, target: Target, name: Match[str]):
    if isinstance(sender, Group):
        res = cards.sa_handler(name.result.lower(), f"g{sender.id}", target.id)
    else:
        res = cards.sa_handler(name.result.lower(), f"f{sender.id}")
    return await app.send_message(sender, res)


@record("coc")
@alcommand(del_c)
async def del_handle(app: Ariadne, sender: Sender, target: Target, data: Match[Tuple[str]]):
    if isinstance(sender, Group):
        res = cards.del_handler([i.lower() for i in data.result], f"g{sender.id}", target.id)
    else:
        res = cards.del_handler([i.lower() for i in data.result], f"f{sender.id}")
    return await app.send_message(sender, "\n".join(res))


@listen(ApplicationShutdown)
async def _save():
    cards.save()
