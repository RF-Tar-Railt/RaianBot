from arclet.alconna import Args, CommandMeta, AllParam, ArgField, Option, set_default
from arclet.alconna.graia import Alconna, alcommand, assign, Match
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, AtAll, Image, Plain
from graia.ariadne.app import Ariadne
from graiax.text2img.playwright.builtin import html2img, PageParams

from app import Sender, record, create_md

m2i = Alconna(
    "文转图",
    Args["mode", "md|chain|html", "chain"],
    Option("--width|w", Args["width", int]),
    Option("--height|h", Args["height", int]),
    Args["content", AllParam, ArgField(completion=lambda: "插入个图片？")],
    meta=CommandMeta("文字转图片", usage="可以选择 md 或 chain 模式", example="$文转图 --width 640 \\n# H1"),
    behaviors=[set_default(640, "width", "width"), set_default(480, "height", "height")]
)


@alcommand(m2i)
@record("t2i")
@assign("mode", "chain", True)
async def chain(app: Ariadne, sender: Sender, message: MessageChain, width: Match[int]):
    message = message.as_sendable()
    if isinstance((text := message.content[0]), Plain):
        assert isinstance(text, Plain)
        string = text.text
        string = (''.join(string.split("文转图")[1:])).replace("chain", "")
        content = message.content[1:]
        content.insert(0, Plain(string))
    else:
        content = message.content[:]
    md = ""
    for elem in content:
        if isinstance(elem, str):
            elem = elem.replace("\n\n", "\n").replace("\n", "\n\n").replace("#", "&#35;").replace(">", "&gt;")
            md += elem
        elif isinstance(elem, Plain):
            text = elem.text.replace("\n\n", "\n").replace("\n", "\n\n").replace("#", "&#35;").replace(">", "&gt;")
            md += text
        elif isinstance(elem, Image):
            md += f"\n![]({elem.url})\n"
        elif isinstance(elem, At):
            md += f"[@{elem.representation or elem.target}]()"
        elif isinstance(elem, AtAll):
            md += "[@全体成员]()"
        else:
            md += str(elem).replace("\n\n", "\n").replace("\n", "\n\n").replace("#", "&#35;").replace(">", "&gt;")
    return app.send_message(sender, MessageChain(Image(data_bytes=await create_md(
        md, width=width.result, height=(md.count('\n') + 5) * 16
    ))))


@alcommand(m2i)
@record("t2i")
@assign("mode", "html")
async def html(app: Ariadne, sender: Sender, message: MessageChain, width: Match[int], height: Match[int]):
    return app.send_message(sender, MessageChain(
        Image(data_bytes=await html2img(
            '\n'.join((str(message).split("\n")[1:])),
            page_params=PageParams(viewport={"width": width.result, "height": height.result})
        ))))


@alcommand(m2i)
@record("t2i")
@assign("mode", "md")
async def mad(app: Ariadne, sender: Sender, message: MessageChain, width: Match[int]):
    return app.send_message(sender, MessageChain(
        Image(data_bytes=await create_md(
            res := '\n'.join(content := (str(message).split("\n")[1:])),
            width=((max(len(i) for i in content) + 5) * 16 if content else width.result),
            height=(res.count('\n') + 5) * 16))
    ))
