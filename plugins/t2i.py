from arclet.alconna import Args, CommandMeta, AllParam, ArgField, Arpamar
from arclet.alconna.graia import Alconna, alcommand, assign
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, AtAll, Image
from graia.ariadne.app import Ariadne
from graiax.text2img.playwright.builtin import md2img
from app import Sender, record

m2i = Alconna(
    "文转图",
    Args["mode", "md|chain", "chain"],
    Args["content", AllParam, ArgField(completion=lambda: "插入个图片？")],
    meta=CommandMeta("文字转图片", usage="可以选择 md 或 chain 模式", keep_crlf=True),
)


@record("t2i")
@assign("mode", "chain", True)
@alcommand(m2i)
async def chain(app: Ariadne, sender: Sender, result: Arpamar):
    content = result.query("content", [])
    md = ""
    for elem in content:
        if isinstance(elem, str):
            elem = elem.replace("\n\n", "\n").replace("\n", "\n\n")
            md += elem
        elif isinstance(elem, Image):
            md += f"\n![]({elem.url})\n"
        elif isinstance(elem, At):
            md += f"[@{elem.representation or elem.target}]()"
        elif isinstance(elem, AtAll):
            md += "[@全体成员]()"
        else:
            md += str(elem)
    return app.send_message(sender, MessageChain(Image(data_bytes=await md2img(md))))


@record("t2i")
@assign("mode", "md")
@alcommand(m2i)
async def mad(app: Ariadne, sender: Sender, result: Arpamar):
    return app.send_message(sender, MessageChain(
        Image(data_bytes=await md2img(''.join(result.query("content", []))))
    ))
