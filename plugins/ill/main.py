import json
import random
from typing import Union

from arclet.alconna import Alconna, Args, CommandMeta, Field, Option
from arclet.alconna.graia import Match, alcommand
from avilla.core import Context, Nick, Notice
from avilla.elizabeth.account import ElizabethAccount

from app.shortcut import accessable, allow, exclusive, record

json_filename = "assets/data/ill_templates.json"
with open(json_filename, encoding="UTF-8") as f_obj:
    ill_templates = json.load(f_obj)["templates"]

ill = Alconna(
    "发病",
    Args["name?#你想对谁发病", [str, Notice]],
    Option(
        "模板|模版",
        Args["template", list(ill_templates.keys()), Field(completion=lambda: list(ill_templates.keys()))],
        dest="tp",
        help_text="指定发病模板",
    ),
    meta=CommandMeta(
        "生成一段模板文字",
        usage="若不指定模板则会随机挑选一个",
        example="$发病 老公",
        extra={"supports": {"mirai"}},
    ),
)


@alcommand(ill, send_error=True)
@allow(ElizabethAccount)
@record("发病")
@exclusive
@accessable
async def ill_(ctx: Context, name: Match[Union[str, Notice]], template: Match[str]):
    """依据模板发病"""
    if template.available:
        tp = ill_templates[template.result]
    else:
        tp = random.choice(list(ill_templates.values()))
    if name.available:
        _name = name.result
        if isinstance(_name, str):
            text = tp.format(target=_name[:20])
        else:
            text = tp.format((_name.display or (await ctx.client.pull(Nick)).nickname)[:20])
    else:
        text = tp.format((await ctx.client.pull(Nick)).nickname[:20])
    return await ctx.scene.send_message(text)
