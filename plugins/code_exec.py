# coding: utf-8
import asyncio
import contextlib
import subprocess
import sys
from io import StringIO

from app import (
    RaianBotInterface,
    Sender,
    create_image,
    render_markdown,
    permission,
    reports_md,
)
from arclet.alconna import Alconna, Field, Args, Arparma, CommandMeta, Option, MultiVar
from arclet.alconna.graia import alcommand, shortcuts, startswith
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graiax.shortcut.saya import listen

code = Alconna(
    "执行",
    Args["code", MultiVar(str), Field(completion=lambda: "试试 print(1+1)")] / "\n",
    Option("out", Args["name", str, "res"]),
    meta=CommandMeta(description="执行简易代码", example="$执行 print(1+1)", hide=True),
)


@shortcuts(
    命令概览=MessageChain(f"{code.headers[0]}执行\nfrom arclet.alconna import command_manager\nprint(command_manager)"),  # type: ignore
)
@alcommand(code, send_error=True)
@permission("admin")
async def execc(app: Ariadne, sender: Sender, result: Arparma, interface: RaianBotInterface):
    codes = str(result.origin).split("\n")
    output = result.query("out.name", "res")
    if len(codes) == 1:
        return
    for _code in codes[1:]:
        if "exit(" in _code or "os." in _code or "system(" in _code or "while" in _code or "attr" in _code:
            return await app.send_message(sender, MessageChain("Execution terminated"))
    lcs = {}
    _stdout = StringIO()
    _to = sys.stdout
    sys.stdout = _stdout
    try:
        glb = globals().copy()
        glb.pop("open", None)
        glb.pop("eval", None)
        glb.pop("exec", None)
        glb["config"] = interface.config
        glb["data"] = interface.data
        exec(
            "async def rc(__out: str):\n    "
            + "    ".join(_code + "\n" for _code in codes[1:])
            + "    await asyncio.sleep(0.1)\n"
            + "    return locals().get(__out)",
            {**glb, **locals()},
            lcs,
        )
        code_res = await asyncio.wait_for(lcs["rc"](output), 10)
        sys.stdout = _to
        if code_res is not None:
            return await app.send_message(
                sender,
                MessageChain(Image(data_bytes=(await create_image(f"{output}: {code_res}", cut=120)))),
            )
        _out = _stdout.getvalue()
        return await app.send_message(
            sender,
            MessageChain(Image(data_bytes=(await create_image(f"output: {_out}", cut=120)))),
        )
    except Exception as e:
        sys.stdout = _to
        return await app.send_message(
            sender,
            MessageChain(Image(data_bytes=(await render_markdown(reports_md(e))))),
        )
    finally:
        sys.stdout = _to


@listen(GroupMessage, FriendMessage)
@permission("master")
@startswith("shell", bind="echos")
async def shell(app: Ariadne, sender: Sender, echos: MessageChain):
    with contextlib.suppress(asyncio.TimeoutError):
        process = await asyncio.wait_for(
            asyncio.create_subprocess_shell(
                str(echos),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=True,
            ),
            timeout=20,
        )
        data = await asyncio.wait_for(process.stdout.read(), timeout=20)
        try:
            res = data.decode("utf-8")
        except UnicodeDecodeError:
            res = data.decode("gbk")
        md = f"""\
```sh
{res}
```
"""
        return await app.send_message(
            sender,
            MessageChain(
                Image(
                    data_bytes=(
                        await render_markdown(
                            md,
                            width=max(max(len(i.strip()) for i in md.splitlines()) * 14, 240),
                            height=(md.count("\n") + 7) * 14,
                        )
                    )
                )
            ),
        )
    return
