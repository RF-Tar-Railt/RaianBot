import asyncio
import sys
import traceback
from io import StringIO
from secrets import token_hex

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Field, MultiVar, Option
from arclet.alconna.graia import alcommand
from avilla.core import ActionFailed, Context, Picture, RawResource
from graiax.playwright import PlaywrightService
from nepattern import AnyString

from app.core import RaianBotService
from app.database import DatabaseService
from app.image import md2img, text2img
from app.shortcut import accessable, exclusive, permission, picture

code = Alconna(
    "执行",
    Args["code", MultiVar(AnyString), Field(completion=lambda: "试试 print(1+1)")] / "\n",
    Option("--pure-text"),
    Option("--no-output"),
    Option("--timeout", Args["sec", int]),
    Option("--out", Args["name", str, "res"]),
    meta=CommandMeta("执行简易代码", example="$执行\nprint(1+1)", hide=True, extra={"supports": {"mirai", "qqapi"}}),
)
code.shortcut(
    "命令概览",
    command=(
        "执行\n"
        "from arclet.alconna import command_manager\n"
        "for k, v in enumerate(command_manager.records.items()[:40]):\n"
        "    print(f'[{k}]: {v[1].origin}')\n"
    ),
    prefix=True,
)
code.shortcut(
    "echo",
    command="执行 --no-output --pure-text\nawait ctx.scene.send_message(\\'{*}\\')",
    prefix=True,
)

code.shortcut(
    "(?:https?://)?github.com/(.+)/([^#]+).*?",
    command="""\
/执行 --no-output --pure-text
import secrets
from avilla.core import UrlResource
token = secrets.token_urlsafe(16)
url = \\'https://opengraph.githubassets.com/\\' + token + \\'/{0}/{1}\\'
await ctx.scene.send_message(Picture(UrlResource(url)))
    """,
)


@alcommand(code, send_error=True, post=True)
@permission("admin")
@exclusive
@accessable
async def execc(ctx: Context, result: Arparma, bot: RaianBotService, pw: PlaywrightService, db: DatabaseService):
    if result.find("pure-text"):
        codes = [""] + list(result.code)
    else:
        codes = str(result.origin).split("\n")
    output = result.query("out.name", "res")
    if len(codes) == 1:
        return
    for _code in codes[1:]:
        if "exit(" in _code or "os." in _code or "system(" in _code or "while" in _code or "attr" in _code:
            return await ctx.scene.send_message("Execution terminated")
    lcs = {}
    _stdout = StringIO()
    _to = sys.stdout
    sys.stdout = _stdout
    try:
        glb = globals().copy()
        glb.pop("open", None)
        glb.pop("eval", None)
        glb.pop("exec", None)
        exec(
            "async def rc(__out: str):\n    "
            + "    ".join(_code + "\n" for _code in codes[1:])
            + "    await asyncio.sleep(0.1)\n"
            + "    return locals().get(__out)",
            {**glb, **locals()},
            lcs,
        )
        code_res = await asyncio.wait_for(lcs["rc"](output), result.query[int]("timeout.sec", 10))
        sys.stdout = _to
        if result.find("no-output"):
            return
        if code_res is not None:
            img = await text2img(f"{output}: {code_res}")
            try:
                return await ctx.scene.send_message(Picture(RawResource(img)))
            except Exception:
                url = await bot.upload_to_cos(img, f"code_exec_{token_hex(16)}.jpg")
                try:
                    return await ctx.scene.send_message(picture(url, ctx))
                except ActionFailed:
                    return await ctx.scene.send_message(f"{output}: {code_res}")
        _out = _stdout.getvalue().replace("<", "&lt;").replace(">", "&gt;")
        img = await text2img(f"output:\n{_out}")
        try:
            return await ctx.scene.send_message(Picture(RawResource(img)))
        except Exception:
            url = await bot.upload_to_cos(img, f"code_exec_{token_hex(16)}.jpg")
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed:
                return await ctx.scene.send_message(f"output: {_out}")
    except Exception as e:
        sys.stdout = _to
        with StringIO() as fp:
            traceback.print_tb(e.__traceback__, file=fp)
            tb = fp.getvalue()
        img = await md2img(
            f"""\
## 异常类型：

`{type(e)}`

## 异常内容：

{str(e)}

## 异常追踪：
```py
{tb}
```
"""
        )
        try:
            return await ctx.scene.send_message(Picture(RawResource(img)))
        except Exception:
            url = await bot.upload_to_cos(img, f"code_exec_{token_hex(16)}.jpg")
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed:
                return await ctx.scene.send_message("\n".join(tb.splitlines()[-10:]) + "\n" + repr(e))
    finally:
        sys.stdout = _to
