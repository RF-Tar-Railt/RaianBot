import json
import random
from arclet.alconna import Args, Empty, Option, Arparma, Field, CommandMeta
from arclet.alconna.graia import Alconna, alcommand, fetch_name
from graia.ariadne.message.element import At
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.app import Ariadne
from graiax.shortcut.saya import decorate

from app import Sender, record, accessable, exclusive

json_filename = "assets/data/ill_templates.json"
with open(json_filename, "r", encoding="UTF-8") as f_obj:
    ill_templates = json.load(f_obj)["templates"]

ill = Alconna(
    "发病",
    Args["name#你想对谁发病", [str, At], Empty],
    Option(
        "模板|模版",
        Args["template", list(ill_templates.keys()), Field(completion=lambda: list(ill_templates.keys()))],
        dest="tp",
        help_text="指定发病模板",
    ),
    meta=CommandMeta(description="生成一段模板文字", usage="若不指定模板则会随机挑选一个", example="$发病 老公")
)


@alcommand(ill, send_error=True)
@record("发病")
@decorate({"name": fetch_name()})
@exclusive
@accessable
async def ill_(app: Ariadne, sender: Sender, name: str, result: Arparma):
    """依据模板发病"""
    if result.find("tp"):
        template = ill_templates[result.query("tp.template")]
    else:
        template = random.choice(list(ill_templates.values()))
    return await app.send_message(sender, MessageChain(template.format(target=name[:20])))
