import json
import random
from arclet.alconna import Args, Empty, Option, Arpamar
from arclet.alconna.graia import Alconna
from graia.ariadne.message.element import At
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Friend
from graia.ariadne.app import Ariadne

from app import command, Sender, Target, record

json_filename = "assets/data/ill_templates.json"
with open(json_filename, 'r', encoding='UTF-8') as f_obj:
    ill_templates = json.load(f_obj)['templates']

ill = Alconna(
    "发病", Args["name", [str, At], Empty],
    options=[Option("模板", Args["template", list(ill_templates.keys())], help_text="指定发病模板")],
    help_text="生成一段模板文字 Usage: 若不指定模板则会随机挑选一个; Example: $发病 老公;",
)


@command(ill)
@record("发病")
async def test2(app: Ariadne, sender: Sender, target: Target, result: Arpamar):
    """依据模板发病"""
    if result.name:
        if isinstance(result.name, At):
            name = result.name.display
            if not name:
                name = (await app.getUserProfile(result.name.target)).nickname
        else:
            name = result.name
    elif isinstance(target, Friend):
        name = target.nickname
    else:
        name = target.name
    if result.find("模板"):
        template = ill_templates[result.query("模板.template")]
    else:
        template = random.choice(list(ill_templates.values()))
    return await app.send_message(sender, MessageChain(template.format(target=name)))
