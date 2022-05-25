# coding: utf-8
import traceback
import subprocess
import asyncio
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
    "执行", Args["code;S":str],
    headers=bot.config.command_prefix,
    options=[Option("out", Args["name;O":str:"res"])],
    help_text="执行简易代码 Example: 莱安执行 print(1+1);",
)

shell = Alconna(
    "shell", Args["code":AllParam],
    headers=bot.config.command_prefix,
    help_text="执行命令行语句 Example: 莱安执行 echo hello;",
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=code, help_flag="reply")))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot.config.master_id, include_ids=True)])
)
async def _(app: Ariadne, sender: Union[Group, Friend], message: MessageChain, result: AlconnaProperty):
    arp = result.result
    codes = message.asDisplay().split("\n")
    output = arp.query("out.name", "res")
    if len(codes) == 1:
        return
    for _code in codes[1:]:
        if "exit(" in _code or "os." in _code or "system(" in _code:
            return await app.sendMessage(sender, MessageChain.create("Execution terminated"))
    lcs = {}
    try:
        exec(
            "async def rc():\n    " +
            "    ".join([_code + "\n" for _code in codes[1:]]) +
            "    await asyncio.sleep(0.1)\n" +
            "    return locals()", {**globals(), **locals()}, lcs
        )
        print(lcs['rc'])
        data = await lcs['rc']()
        code_res = data.get(output)
        if code_res is not None:
            return await app.sendMessage(sender, MessageChain.create(f"{output}: {code_res}"))
        else:
            return await app.sendMessage(sender, MessageChain.create("execute success"))
    except Exception as e:
        return await app.sendMessage(
            sender, MessageChain.create(
                '\n'.join(traceback.format_exception(e.__class__, e, e.__traceback__, limit=1))
            )
        )


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=shell, help_flag="reply")))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot.config.master_id, include_ids=True)])
)
async def _(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    try:
        res = subprocess.run(result.result.main_args['code'], capture_output=True).stdout.decode('gbk')
    except UnicodeDecodeError:
        res = subprocess.run(result.result.main_args['code'], capture_output=True).stdout.decode('utf-8')
    await asyncio.sleep(0)
    return await app.sendMessage(sender, MessageChain.create(Image(data_bytes=(await create_image(res, cut=120)))))
