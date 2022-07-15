import asyncio
from arclet.alconna import Args, Option, Arpamar
from arclet.alconna.graia import Alconna, Match, command, match_path
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image  # Forward, ForwardNode
from graia.ariadne.model import Group
from graia.ariadne.app import Ariadne
from graia.ariadne.util.saya import decorate

from app import RaianMain, Sender, require_admin
from utils.generate_img import create_image

shutdown = Alconna(
    "关机",
    Args["time", int, 0],
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
    help_text="管理机器人的模块 Example: $模块 列出\n $模块 卸载 setu;"
)

function_control = Alconna(
    "功能",
    options=[
        Option("列出", alias=['list']),
        Option("禁用", Args['name', str], alias=['ban'], help_text="禁用一个功能"),
        Option("启用", Args['name', str], alias=['active'], help_text="启用一个功能")
    ],
    help_text="管理机器人的功能 Example: $功能 列出\n $功能 禁用 greet;"
)


@command(Alconna("调试", help_text="显示调试信息"))
@decorate(require_admin())
async def debug(app: Ariadne, sender: Sender, bot: RaianMain):
    mds = f"当前共加载模块：{len(bot.saya.channels)}个\n已禁用模块: {bot.config.disabled_plugins}"
    groups_debug = f"当前共加入群：{len(bot.data.groups)}个"
    users_debug = f"当前共有：{len(bot.data.users)}人参与签到"
    res = [mds, groups_debug, users_debug]
    if isinstance(sender, Group):
        group = bot.data.get_group(sender.id)
        fns = "所在群组已列入黑名单" if group.in_blacklist else f"所在群组已禁用功能: {group.disabled}"
        res.append(fns)
    return await app.send_message(sender, MessageChain("\n".join(res)))


@command(shutdown)
@decorate(require_admin(True))
async def _s(app: Ariadne, sender: Sender, time: Match[int], bot: RaianMain):
    await app.send_message(sender, MessageChain("正在关机。。。"))
    await asyncio.sleep(time.result)
    bot.stop()
    await asyncio.sleep(0.1)


@command(module_control, send_error=True)
@decorate(require_admin(True), match_path("列出"))
async def _m_list(app: Ariadne, sender: Sender, bot: RaianMain):
    saya = bot.saya
    res = "=================================\n"
    enables = list(saya.channels.keys())
    e_max = max(len(i) for i in enables) if saya.channels else 0
    d_max = max(
        (len(i) + len(bot.config.plugin_path) + 1)
        for i in bot.config.disabled_plugins
    ) if bot.config.disabled_plugins else 0
    l_max = max(e_max, d_max)
    for name in enables:
        res += name.ljust(l_max + 1) + "已安装\n"
    for name in bot.config.disabled_plugins:
        res += f'{bot.config.plugin_path}.{name}'.ljust(l_max + 1) + "已卸载\n"
    res += "================================="
    return await app.send_message(
        sender, MessageChain(Image(data_bytes=await create_image(res)))
    )


@command(module_control, send_error=True)
@decorate(require_admin(True), match_path("卸载"))
async def _m_uninstall(app: Ariadne, sender: Sender, name: Match[str], bot: RaianMain):
    saya = bot.saya
    channel_name = (name.result.split(".")[-1]) if name.available else 'control'
    if channel_name == "control":
        return
    parent = bot.config.plugin_path
    module_path = f"{parent}.{channel_name}"
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


@command(module_control, send_error=True)
@decorate(require_admin(True), match_path("安装"))
async def _m_install(app: Ariadne, sender: Sender, name: Match[str], bot: RaianMain):
    saya = bot.saya
    channel_name = (name.result.split(".")[-1]) if name.available else 'control'
    if channel_name == "control":
        return
    parent = bot.config.plugin_path
    module_path = f"{parent}.{channel_name}"
    if channel_name in saya.channels and channel_name not in bot.config.disabled_plugins:
        return await app.send_message(sender, MessageChain("该模组已安装"))
    try:
        with bot.context.use(bot):
            with saya.module_context():
                saya.require(module_path)
    except Exception as e:
        await app.send_message(sender, MessageChain(f"安装 {module_path} 失败！"))
        raise e
    else:
        if channel_name in bot.config.disabled_plugins:
            bot.config.disabled_plugins.remove(channel_name)
        return await app.send_message(sender, MessageChain(f"安装 {module_path} 成功"))


@command(module_control, send_error=True)
@decorate(require_admin(True), match_path("重载"))
async def _m_reload(app: Ariadne, sender: Sender, name: Match[str], bot: RaianMain):
    saya = bot.saya
    channel_name = (name.result.split(".")[-1]) if name.available else 'control'
    if channel_name == "control":
        return
    parent = bot.config.plugin_path
    module_path = f"{parent}.{channel_name}"
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


@command(module_control, send_error=True)
@decorate(require_admin(True), match_path("$main"))
async def _m_main(app: Ariadne, sender: Sender):
    return await app.send_message(sender, MessageChain(module_control.get_help()))


@command(function_control, private=False, send_error=True)
@decorate(require_admin(True))
async def _f(app: Ariadne, sender: Group, result: Arpamar, name: Match[str], bot: RaianMain):
    if not result.options:
        return await app.send_message(sender, MessageChain(function_control.get_help()))
    group = bot.data.get_group(sender.id)
    if result.find('列出'):
        res = f"{sender.name} / {sender.id} 统计情况\n"
        res += "====================================\n"
        funcs = [f"{i}  备注: {bot.data.func_description(i)}" for i in bot.data.funcs]
        for sign, nm in zip(funcs, bot.data.funcs):
            res += f"{'【禁用】' if nm in group.disabled or group.in_blacklist else '【启用】'} {sign}" + "\n"
        res += "===================================="
        return await app.send_message(
            sender, MessageChain(Image(data_bytes=(await create_image(res))))
        )
    if not name.available:
        return await app.send_message(sender, MessageChain("该功能未找到"))
    name = name.result
    if group.in_blacklist or sender.id in bot.data.cache['blacklist']:
        return await app.send_message(sender, MessageChain("所在群组已进入黑名单, 设置无效"))
    if result.find("禁用"):
        if name in group.disabled:
            return await app.send_message(sender, MessageChain(f"功能 {name} 已经禁用"))
        group.disabled.append(name)
        bot.data.update_group(group)
        return await app.send_message(sender, MessageChain(f"功能 {name} 禁用成功"))
    if result.find("启用"):
        if name not in group.disabled:
            return await app.send_message(sender, MessageChain(f"功能 {name} 未禁用"))
        group.disabled.remove(name)
        bot.data.update_group(group)
        return await app.send_message(sender, MessageChain(f"功能 {name} 启用成功"))
