import asyncio
import sys
from io import StringIO

from app import RaianBotInterface, Sender, create_image, render_markdown, permission, reports_md, exclusive, accessable
from nepattern import AnyString
from arclet.alconna import Alconna, Field, Args, Arparma, CommandMeta, Option, MultiVar
from arclet.alconna.graia import alcommand, startswith
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import FriendMessage, GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graiax.shortcut.saya import listen

code = Alconna(
    "执行",
    Args["code", MultiVar(AnyString), Field(completion=lambda: "试试 print(1+1)")] / "\n",
    Option("--pure-text"),
    Option("--no-output"),
    Option("--timeout", Args["sec", int]),
    Option("--out", Args["name", str, "res"]),
    meta=CommandMeta(description="执行简易代码", example="$执行 print(1+1)", hide=True),
)
code.shortcut(
    "命令概览",
    {
        "command": MessageChain(
            f"{code.headers[0]}执行\nfrom arclet.alconna import command_manager\nprint(command_manager)"
        )
    },
)
code.shortcut(
    "echo",
    {
        "command": MessageChain(
            f"{code.headers[0]}执行 --no-output --pure-text\n"
            f"await app.send_message(sender, \\'{{*}}\\')"
        )
    },
)
code.shortcut(
    "render",
    {
        "command": MessageChain(
            f"{code.headers[0]}执行 --no-output --pure-text --timeout 60\n"
            f"from graiax.playwright import PlaywrightBrowser\n"
            f"browser = app.launch_manager.get_interface(PlaywrightBrowser)\n"
            f"page = await browser.new_page()\n"
            f"await page.click(\\'html\\')\n"
            f"await page.goto(\\'{{%0}}\\')\n"
            f"data = await page.screenshot(full_page=True)\n"
            f"await app.send_message(sender, MessageChain(Image(data_bytes=data)))\n"
            f"await page.close()\n"
        )
    },
)


code.shortcut(
    "(?:https?://)?github.com/(.+)/([^#]+).*?",
    {
        "command": MessageChain(
            f"{code.headers[0]}执行 --no-output --pure-text --timeout 60\n"
            f"import secrets\n"
            f"token = secrets.token_urlsafe(16)\n"
            f"resp = await app.service.client_session.get(\\'https://opengraph.githubassets.com/\\' + token + \\'/{{0}}/{{1}}\\').__aenter__()\n"
            f"data = await resp.read()\n"
            f"await app.send_message(sender, MessageChain(Image(data_bytes=data)))\n"
            f"await resp.__aexit__(None, None, None)"
        )
    },
)


@alcommand(code, send_error=True)
@permission("admin")
@exclusive
@accessable
async def execc(app: Ariadne, sender: Sender, result: Arparma, interface: RaianBotInterface):
    if result.find("pure-text"):
        codes = [""] + list(result.code)
    else:
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
        code_res = await asyncio.wait_for(lcs["rc"](output), result.query("timeout.sec", 10))
        sys.stdout = _to
        if result.find("no-output"):
            return
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
@exclusive
@accessable
async def shell(app: Ariadne, sender: Sender, echos: MessageChain):
    process = await asyncio.create_subprocess_shell(
        str(echos),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), 20)
    except asyncio.TimeoutError:
        process.kill()
        stdout, stderr = await process.communicate()
    if stdout:
        try:
            res = stdout.decode("utf-8").strip()
        except UnicodeDecodeError:
            res = stdout.decode("gbk").strip()
    elif stderr:
        try:
            res = stderr.decode("utf-8").strip()
        except UnicodeDecodeError:
            res = stderr.decode("gbk").strip()
    else:
        res = "No output"
    md = f"""\
> exit code: {process.returncode}

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
