import asyncio
from typing import Union
from arclet.alconna import Args, Option
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya import Channel, Saya
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image  # Forward, ForwardNode
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend
from graia.ariadne.app import Ariadne

from app import RaianMain
from utils.control import require_admin
from utils.generate_img import create_image

bot = RaianMain.current()
saya = Saya.current()
channel = Channel.current()

shutdown = Alconna(
    "关机",
    Args["time", int, 0],
    headers=bot.config.command_prefix,
    help_text="关闭机器人",
)

module_control = Alconna(
    "模块",
    options=[
        Option("列出", alias=['list']),
        Option("卸载", Args['name', str], alias=["关闭", "uninstall"], help_text="安装一个模块"),
        Option("安装", Args['name', str], alias=["开启", "install"], help_text="卸载一个模块"),
        Option("重载", Args['name', str], alias=["重启", "reload"], help_text="重新载入一个模块")
    ],
    headers=bot.config.command_prefix,
    help_text="管理机器人的模块"
)

function_control = Alconna(
    "功能",
    options=[
        Option("列出", alias=['list']),
        Option("禁用", Args['name', str], alias=['ban'], help_text="禁用一个功能"),
        Option("启用", Args['name', str], alias=['active'], help_text="启用一个功能")
    ],
    headers=bot.config.command_prefix,
    help_text="管理机器人的功能"
)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=shutdown, help_flag="reply")))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot.config.master_id, include_ids=True)])
)
async def _s(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    await app.send_message(sender, MessageChain("正在关机。。。"))
    await asyncio.sleep(result.result.time)
    bot.stop()
    await asyncio.sleep(0.1)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=module_control, help_flag='reply')))
@channel.use(
    ListenerSchema([GroupMessage, FriendMessage], decorators=[require_admin(bot.config.master_id, include_ids=True)])
)
async def _m(app: Ariadne, sender: Union[Group, Friend], result: AlconnaProperty):
    arp = result.result
    if arp.find("列出"):
        res = "=================================\n"
        enables = [i for i in saya.channels.keys()]
        e_max = max(len(i) for i in enables)
        d_max = max(
            (len(i) + len(bot.config.plugin_path) + 1)
            for i in bot.config.disabled_plugins
        )
        l_max = max(e_max, d_max)
        for name in enables:
            res += name.ljust(l_max + 1) + "已安装\n"
        for name in bot.config.disabled_plugins:
            res += (bot.config.plugin_path + '.' + name).ljust(l_max + 1) + "已卸载\n"
        res += "================================="
        return await app.send_message(
            sender, MessageChain(Image(data_bytes=await create_image(res)))
        )
    channel_name = arp.other_args.get("name", "control").split(".")[-1]
    if channel_name == "control":
        return
    parent = bot.config.plugin_path
    module_path = f"{parent}.{channel_name}"
    if arp.find("卸载"):
        if not (_channel := saya.channels.get(module_path)):
            return await app.send_message(sender, MessageChain("该模组未安装, 您可能需要安装它"))
        try:
            saya.uninstall_channel(_channel)
        except Exception as e:
            await app.send_message(sender, MessageChain(f"卸载 {module_path} 失败！"))
            raise e
        else:
            bot.config.disabled_plugins.append(channel_name)
            return await app.send_message(sender, MessageChain(f"卸载 {module_path} 成功"))
    if arp.find("安装"):
        if channel_name not in bot.config.disabled_plugins:
            return await app.send_message(sender, MessageChain("该模组已安装"))
        try:
            with bot.context.use(bot):
                with saya.module_context():
                    saya.require(module_path)
        except Exception as e:
            await app.send_message(sender, MessageChain(f"安装 {module_path} 失败！"))
            raise e
        else:
            bot.config.disabled_plugins.remove(channel_name)
            return await app.send_message(sender, MessageChain(f"安装 {module_path} 成功"))
    if arp.find("重载"):
        if not (_channel := saya.channels.get(module_path)):
            return await app.send_message(sender, MessageChain("该模组未安装, 您可能需要安装它"))
        try:
            with bot.context.use(bot):
                with saya.module_context():
                    saya.reload_channel(_channel)
        except Exception as e:
            await app.send_message(sender, MessageChain(f"重载 {module_path} 失败！"))
            raise e
        else:
            return await app.send_message(sender, MessageChain(f"重载 {module_path} 成功"))


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=function_control, help_flag='reply')))
@channel.use(
    ListenerSchema([GroupMessage], decorators=[require_admin(bot.config.master_id)])
)
async def _f(app: Ariadne, sender: Group, result: AlconnaProperty):
    arp = result.result
    group = bot.data.get_group(sender.id)
    if arp.find('列出'):
        res = f"{sender.name} / {sender.id} 统计情况\n"
        res += "============================\n"
        funcs = [f"{i}: {bot.data.func_description(i)}" for i in bot.data.funcs]
        l_max = max(len(i) for i in funcs)
        print(l_max)
        for sign, name in zip(funcs, bot.data.funcs):
            res += sign.ljust(l_max + 1) + f"{'禁用' if (name in group.disabled or group.in_blacklist) else '启用'}\n"
        res += "============================"
        return await app.send_message(
            sender, MessageChain(Image(data_bytes=(await create_image(res))))
        )
    name = arp.other_args.get('name')
    if not name:
        return await app.send_message(sender, MessageChain("该功能未找到"))
    if group.in_blacklist or sender.id in bot.data.cache['blacklist']:
        return await app.send_message(sender, MessageChain("所在群组已进入黑名单, 设置无效"))
    if arp.find("禁用"):
        if name in group.disabled:
            return await app.send_message(sender, MessageChain(f"功能 {name} 已经禁用"))
        group.disabled.append(name)
        bot.data.update_group(group)
        return await app.send_message(sender, MessageChain(f"功能 {name} 禁用成功"))
    if arp.find("启用"):
        if name not in group.disabled:
            return await app.send_message(sender, MessageChain(f"功能 {name} 未禁用"))
        group.disabled.remove(name)
        bot.data.update_group(group)
        return await app.send_message(sender, MessageChain(f"功能 {name} 启用成功"))
