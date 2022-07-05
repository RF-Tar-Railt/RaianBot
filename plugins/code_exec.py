# coding: utf-8
import sys
import subprocess
import asyncio
from io import StringIO
from arclet.alconna import Args, AllParam, Option, Alconna, Arpamar
from graia.ariadne.message.element import Image
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.app import Ariadne
from graia.ariadne.util.saya import decorate

from app import Sender, command, require_admin
from utils.generate_img import create_image
from utils.exception_report import generate_reports

code = Alconna(
    "执行", Args["code;S", str],
    options=[Option("out", Args["name;O", str, "res"])],
    help_text="执行简易代码 Example: $执行 print(1+1);",
)


@command(code)
@decorate(require_admin())
async def execc(app: Ariadne, sender: Sender, result: Arpamar):
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
        exec(
            "async def rc():\n    " +
            "    ".join(_code + "\n" for _code in codes[1:]) +
            "    await asyncio.sleep(0.1)\n" +
            "    return locals()", {**glb, **locals()}, lcs
        )
        data = await asyncio.wait_for(lcs['rc'](), 10)
        code_res = data.get(output)
        sys.stdout = _to
        if code_res is not None:
            return await app.send_message(
                sender, MessageChain(Image(
                    data_bytes=(await create_image(f"{output}: {code_res}", cut=120))
                ))
            )
        else:
            out = _stdout.getvalue()
            return await app.send_message(
                sender, MessageChain(Image(
                    data_bytes=(await create_image(f"output: {out}", cut=120))
                ))
            )
    except Exception as e:
        sys.stdout = _to
        return await app.send_message(sender, MessageChain(Image(data_bytes=(await create_image(generate_reports(e))))))
    finally:
        sys.stdout = _to


@command(Alconna("shell", Args["code", AllParam], help_text="执行命令行语句 Example: $shell echo hello;"))
@decorate(require_admin(True))
async def shell(app: Ariadne, sender: Sender, result: Arpamar):
    try:
        res = subprocess.run(
            result.main_args['code'][0],
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ).stdout.decode('utf-8')
    except UnicodeDecodeError:
        res = subprocess.run(
            result.main_args['code'][0],
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ).stdout.decode('gbk')
    await asyncio.sleep(0)
    return await app.send_message(sender, MessageChain(Image(data_bytes=(await create_image(res, cut=120)))))
