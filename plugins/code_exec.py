# coding: utf-8
import sys
import traceback
import subprocess
import asyncio
from io import StringIO
from typing import Union
from arclet.alconna import Args, AllParam, Option
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya import Channel, Saya
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.element import Image
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from app import RaianMain
from utils.generate_img import create_image
from utils.control import require_admin

bot = RaianMain.current()
saya = Saya.current()
channel = Channel.current()

code = Alconna(
    "执行", Args["code;S", str],
    headers=bot.config.command_prefix,
    options=[Option("out", Args["name;O", str, "res"])],
    help_text=f"执行简易代码 Example: {bot.config.command_prefix[0]}执行 print(1+1);",
)

shell = Alconna(
    "shell", Args["code", AllParam],
    headers=bot.config.command_prefix,
    help_text=f"执行命令行语句 Example: {bot.config.command_prefix[0]}shell echo hello;",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=code, help_flag="reply")))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot.config.master_id)])
)
async def _(
        app: Ariadne,
        sender: Union[Group, Friend],
        result: AlconnaProperty
):

    arp = result.result
    codes = str(arp.origin).split("\n")
    output = arp.query("out.name", "res")
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
            return await app.send_message(sender, MessageChain(f"{output}: {code_res}"))
        else:
            out = _stdout.getvalue()
            return await app.send_message(sender, MessageChain(f"output: {out}"))
    except Exception as e:
        sys.stdout = _to
        return await app.send_message(
            sender, MessageChain(
                '\n'.join(traceback.format_exception(e.__class__, e, e.__traceback__, limit=1))
            )
        )
    finally:
        sys.stdout = _to


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=shell, help_flag="reply")))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot.config.master_id, include_ids=True)])
)
async def _(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    arp = result.result
    try:
        res = subprocess.run(
            arp.main_args['code'][0],
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ).stdout.decode('utf-8')
    except UnicodeDecodeError:
        res = subprocess.run(
            arp.main_args['code'][0],
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        ).stdout.decode('gbk')
    await asyncio.sleep(0)
    return await app.send_message(sender, MessageChain(Image(data_bytes=(await create_image(res, cut=120)))))
