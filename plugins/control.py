import asyncio
from arclet.alconna import Args, Option, CommandMeta, ArgField
from arclet.alconna.graia import Alconna, Match, alcommand, assign, AlconnaDispatcher, endswith
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image  # Forward, ForwardNode
from graia.ariadne.model import Group
from graia.ariadne.app import Ariadne
from loguru import logger
from graiax.text2img.playwright.builtin import md2img
from app import RaianMain, Sender, admin, master

module_control = Alconna(
    "模块",
    Option("列出", alias=["list"]),
    Option(
        "卸载",
        Args["name", str, ArgField(completion=lambda: "试试用‘control’")],
        alias=["关闭", "uninstall"],
        help_text="卸载一个模块",
    ),
    Option(
        "安装",
        Args["name", str, ArgField(completion=lambda: "试试用‘control’")],
        alias=["开启", "install"],
        help_text="安装一个模块",
    ),
    Option(
        "重载",
        Args["name", str, ArgField(completion=lambda: "试试用‘control’")],
        alias=["重启", "reload"],
        help_text="重新载入一个模块",
    ),
    meta=CommandMeta("管理机器人的模块", example="$模块 列出\n$模块 卸载 setu"),
)

function_control = Alconna(
    "功能",
    Option("列出", alias=["list"]),
    Option(
        "禁用",
        Args
        ["name", str, ArgField(completion=lambda: "试试用‘greet’")],
        alias=["ban"],
        help_text="禁用一个功能",
    ),
    Option(
        "启用",
        Args
        ["name", str, ArgField(completion=lambda: "试试用‘greet’")],
        alias=["active"],
        help_text="启用一个功能",
    ),
    meta=CommandMeta("管理机器人的功能", example="$功能 列出\n$功能 禁用 greet"),
)

group_control = Alconna(
    "群管",
    Option("当前状态|群组状态|状态|信息", dest="status", help_text="查看当前群组信息"),
    Option("黑名单 列入|加入", dest="add", help_text="将当前群组加入黑名单"),
    Option("黑名单 解除|移出|移除", dest="remove", help_text="将当前群组移出黑名单"),
    Option("退出"),
    meta=CommandMeta("操作当前群组", example="$群管 当前状态\n$群管 黑名单 加入"),
)


@admin
@alcommand(Alconna("调试", meta=CommandMeta("显示调试信息")))
async def debug(app: Ariadne, sender: Sender, bot: RaianMain):
    md = f"""\
# {bot.config.bot_name} 调试信息

## 统计

- 当前共加载模块: {len(bot.saya.channels)}个

- 当前共加入群:   {len(bot.data.groups)}个

- 当前共有:      {len(bot.data.users)}人参与签到
"""
    if bot.config.disabled_plugins:
        md += "\n- 已禁用模块: \n  - " + "\n  - ".join(bot.config.disabled_plugins) + "\n"
    if isinstance(sender, Group):
        md += f"## {sender.name} 相关:\n\n"
        group = bot.data.get_group(sender.id)
        md += ("- 所在群组已列入黑名单\n\n" if group.in_blacklist else "- 所在群组未列入黑名单\n")
        if group.disabled:
            md += "\n- 所在群组已禁用功能: \n  - " + "\n  - ".join(group.disabled) + "\n"
    return await app.send_message(sender, MessageChain(Image(data_bytes=await md2img(md))))


@master
@endswith("关机")
async def _s(app: Ariadne, sender: Sender, bot: RaianMain):
    await app.send_message(sender, MessageChain("正在关机。。。"))
    await asyncio.sleep(0.1)
    bot.stop()
    await asyncio.sleep(0.1)


@assign("列出")
@alcommand(module_control, send_error=True)
async def _m_list(app: Ariadne, sender: Sender, bot: RaianMain):
    saya = bot.saya
    md = f"""\
<div align="center">

# {bot.config.bot_name} 模块信息

| 模块名 | 模块路径 | 状态 |
| ----- | ------- | --- |
"""
    for path, channel in saya.channels.items():
        md += f"| {channel.meta['name'] or path.split('.')[-1]} | {path} | ✔ 已安装 |\n"
    for name in bot.config.disabled_plugins:
        md += f"| {name} | {bot.config.plugin_path}.{name} | ❌ 已卸载 |\n"
    return await app.send_message(
        sender, MessageChain(Image(data_bytes=await md2img(md)))
    )


@master
@assign("卸载")
@alcommand(module_control, send_error=True)
async def _m_uninstall(app: Ariadne, sender: Sender, name: Match[str], bot: RaianMain):
    saya = bot.saya
    channel_name = (name.result.split(".")[-1]) if name.available else "control"
    if channel_name == "control":
        return await app.send_message(sender, MessageChain("该模组未安装, 您可能需要安装它"))
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


@master
@assign("安装")
@alcommand(module_control, send_error=True)
async def _m_install(app: Ariadne, sender: Sender, name: Match[str], bot: RaianMain):
    saya = bot.saya
    channel_name = (name.result.split(".")[-1]) if name.available else "control"
    if channel_name == "control":
        return
    parent = bot.config.plugin_path
    module_path = f"{parent}.{channel_name}"
    if (
        channel_name in saya.channels
        and channel_name not in bot.config.disabled_plugins
    ):
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


@master
@assign("重载")
@alcommand(module_control, send_error=True)
async def _m_reload(app: Ariadne, sender: Sender, name: Match[str], bot: RaianMain):
    saya = bot.saya
    channel_name = (name.result.split(".")[-1]) if name.available else "control"
    if channel_name == "control":
        return
    parent = bot.config.plugin_path
    module_path = f"{parent}.{channel_name}"
    if not (_channel := saya.channels.get(module_path)):
        return await app.send_message(sender, MessageChain("该模组未安装, 您可能需要安装它"))
    try:
        saya.uninstall_channel(_channel)
    except Exception as e:
        await app.send_message(sender, MessageChain(f"重载 {module_path} 过程中卸载失败！"))
        raise e
    try:
        with bot.context.use(bot):
            with saya.module_context():
                saya.require(module_path)
    except Exception as e:
        await app.send_message(sender, MessageChain(f"重载 {module_path} 过程中安装失败！"))
        raise e
    else:
        return await app.send_message(sender, MessageChain(f"重载 {module_path} 成功"))


@assign("$main")
@alcommand(module_control, send_error=True)
async def _m_main(app: Ariadne, sender: Sender):
    return await app.send_message(sender, await AlconnaDispatcher.default_send_handler(module_control.get_help()))


@assign("$main")
@alcommand(function_control, send_error=True)
async def _f_main(app: Ariadne, sender: Sender):
    return await app.send_message(sender, await AlconnaDispatcher.default_send_handler(function_control.get_help()))


@assign("列出")
@alcommand(function_control, private=False, send_error=True)
async def _f_list(app: Ariadne, sender: Group, bot: RaianMain):
    group = bot.data.get_group(sender.id)
    md = f"""\
<div align="center">

# {bot.config.bot_name} 功能概览

## f"{sender.name} / {sender.id} 统计情况

| 名称 | 状态 | 功能备注 |
| ----- | ------- | --- |
"""
    for i in bot.data.funcs:
        stat = "❌ 禁用" if i in group.disabled else "🚫 黑名单" if group.in_blacklist else "✔ 启用"
        md += f"| {i} | {stat} | {bot.data.func_description(i)}{'(默认禁用)' if i in bot.data.disable_functions else ''} |\n"
    return await app.send_message(
        sender, MessageChain(Image(data_bytes=(await md2img(md))))
    )


@admin
@assign("启用")
@alcommand(function_control, private=False, send_error=True)
async def _f_active(app: Ariadne, sender: Group, name: Match[str], bot: RaianMain):
    group = bot.data.get_group(sender.id)
    if not name.available:
        return await app.send_message(sender, MessageChain("该功能未找到"))
    name = name.result
    if group.in_blacklist or sender.id in bot.data.cache["blacklist"]:
        return await app.send_message(sender, MessageChain("所在群组已进入黑名单, 设置无效"))
    if name not in bot.data.funcs:
        return await app.send_message(sender, MessageChain(f"功能 {name} 不存在"))
    if name not in group.disabled:
        return await app.send_message(sender, MessageChain(f"功能 {name} 未禁用"))
    group.disabled.remove(name)
    bot.data.update_group(group)
    return await app.send_message(sender, MessageChain(f"功能 {name} 启用成功"))


@admin
@assign("禁用")
@alcommand(function_control, private=False, send_error=True)
async def _f(app: Ariadne, sender: Group, name: Match[str], bot: RaianMain):
    group = bot.data.get_group(sender.id)
    if not name.available:
        return await app.send_message(sender, MessageChain("该功能未找到"))
    name = name.result
    if group.in_blacklist or sender.id in bot.data.cache["blacklist"]:
        return await app.send_message(sender, MessageChain("所在群组已进入黑名单, 设置无效"))
    if name not in bot.data.funcs:
        return await app.send_message(sender, MessageChain(f"功能 {name} 不存在"))
    if name in group.disabled:
        return await app.send_message(sender, MessageChain(f"功能 {name} 已经禁用"))
    group.disabled.append(name)
    bot.data.update_group(group)
    return await app.send_message(sender, MessageChain(f"功能 {name} 禁用成功"))


@assign("$main")
@alcommand(group_control, send_error=True)
async def _g_main(app: Ariadne, sender: Sender):
    return await app.send_message(sender, await AlconnaDispatcher.default_send_handler(group_control.get_help()))


@master
@assign("退出")
@alcommand(group_control, private=False, send_error=True)
async def _g_quit(app: Ariadne, sender: Group, bot: RaianMain):
    await app.send_message(sender, "正在退出该群聊。。。")
    logger.debug(f"quiting from {sender.name}({sender.id})...")
    bot.data.remove_group(sender.id)
    return await app.quit_group(sender)


@assign("status")
@alcommand(group_control, private=False, send_error=True)
async def _g_state(app: Ariadne, sender: Group, bot: RaianMain):
    group = bot.data.get_group(sender.id)
    fns = "所在群组已列入黑名单" if group.in_blacklist else f"所在群组已禁用功能: {group.disabled}"
    return await app.send_message(sender, fns)


@admin
@assign("黑名单_add")
@alcommand(group_control, private=False, send_error=True)
async def _g_bl_add(app: Ariadne, sender: Group, bot: RaianMain):
    group = bot.data.get_group(sender.id)
    if group.in_blacklist or sender.id in bot.data.cache["blacklist"]:
        return await app.send_message(sender, "该群组已加入黑名单!")
    group.in_blacklist = True
    bot.data.update_group(group)
    bot.data.cache["blacklist"].append(sender.id)
    return await app.send_message(sender, "该群组列入黑名单成功!")


@admin
@assign("黑名单_remove")
@alcommand(group_control, private=False, send_error=True)
async def _g_bl_remove(app: Ariadne, sender: Group, bot: RaianMain):
    group = bot.data.get_group(sender.id)
    if group.in_blacklist or sender.id in bot.data.cache["blacklist"]:
        group.in_blacklist = False
        bot.data.update_group(group)
        if sender.id in bot.data.cache["blacklist"]:
            bot.data.cache["blacklist"].remove(sender.id)
        return await app.send_message(sender, "该群组移出黑名单成功!")
    return await app.send_message(sender, "该群组未列入黑名单!")
