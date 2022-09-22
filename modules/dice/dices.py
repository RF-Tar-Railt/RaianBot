# 参考[OlivaDiceDocs](https://oliva.dicer.wiki/userdoc)实现的nonebot2骰娘插件
import contextlib
import random
from typing import Optional
import diro
from .messages import help_en, help_r


def dhr(t, o):
    return 100 if t == 0 and o == 0 else t*10+o


def st():
    result = random.randint(1, 20)
    if result < 4:
        rstr = "右腿"
    elif result < 7:
        rstr = "左腿"
    elif result < 11:
        rstr = "腹部"
    elif result < 16:
        rstr = "胸部"
    elif result < 18:
        rstr = "右臂"
    elif result < 20:
        rstr = "左臂"
    else:
        rstr = "头部"
    return f"D20={result}: 命中了{rstr}"


def en(arg: int) -> str:
    check = random.randint(1, 100)
    if check <= arg and check <= 95:
        return f"判定值{check}，判定失败，技能无成长。"
    plus = random.randint(1, 10)
    r = f"判定值{check}，判定成功，技能成长{arg}+{plus}={arg + plus}"
    return r + "\n温馨提示：如果技能提高到90%或更高，增加2D6理智点数。"


def expr(d: diro.Diro, anum: Optional[int]) -> str:
    d.roll()
    result = d.calc()
    s = f"{d}={(d.detail_expr())}={result}"
    if anum:
        s += "\n"
        if result == 100:
            s += "大失败！"
        elif anum < 50 and result > 95:
            s += f"{result}>95 大失败！"
        elif result == 1:
            s += "大成功！"
        elif result <= anum // 5:
            s += f"检定值{anum} {result}≤{anum//5} 极难成功"
        elif result <= anum // 2:
            s += f"检定值{anum} {result}≤{anum//2} 困难成功"
        elif result <= anum:
            s += f"检定值{anum} {result}≤{anum} 成功"
        else:
            s += f"检定值{anum} {result}>{anum} 失败"
    return s


def rd0(pattern: str, anum: Optional[int] = None):
    d_str = pattern.lower().split("#")
    try:
        d = diro.parse(d_str.pop(0))
        time = 1
        if d_str:
            with contextlib.suppress(ValueError):
                time = int(d_str[0])
        r = expr(d, anum)
        for _ in range(time - 1):
            r += "\n"
            r += expr(d, anum)
        return r
    except ValueError:
        return help_r
