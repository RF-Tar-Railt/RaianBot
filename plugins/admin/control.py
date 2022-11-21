import re
from datetime import datetime
from pathlib import Path
from typing import List

from app import RaianBotInterface, Sender, permission, create_md, send_handler, RaianBotService
from arclet.alconna import ArgField, Args, CommandMeta, Option
from arclet.alconna.graia import (
    Alconna,
    Match,
    alcommand,
    assign,
)
from creart import it
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Forward, ForwardNode, Image
from graia.ariadne.model import Group
from graia.saya import Saya
from graiax.text2img.playwright.builtin import MarkdownToImg
from loguru import logger
from library.aiml.lang_support import is_chinese

module_control = Alconna(
    "模块",
    Option("列出", alias=["list"]),
    Option(
        "卸载",
        Args["path", str, ArgField(completion=lambda: "试试用‘admin’")],
        alias=["关闭", "uninstall"],
        help_text="卸载一个模块",
    ),
    Option(
        "安装",
        Args["path", str, ArgField(completion=lambda: "试试用‘admin’")],
        alias=["开启", "install"],
        help_text="安装一个模块",
    ),
    Option(
        "重载",
        Args["path", str, ArgField(completion=lambda: "试试用‘admin’")],
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
        Args["name", str, ArgField(completion=lambda: "试试用‘greet’")],
        alias=["ban"],
        help_text="禁用一个功能",
    ),
    Option(
        "启用",
        Args["name", str, ArgField(completion=lambda: "试试用‘greet’")],
        alias=["active"],
        help_text="启用一个功能",
    ),
    meta=CommandMeta("管理机器人的功能", example="$功能 列出\n$功能 禁用 greet"),
)

group_control = Alconna(
    "群组",
    Option("当前状态|状态|信息", dest="status", help_text="查看当前群组信息"),
    Option("黑名单 列入|加入", dest="add", help_text="将当前群组加入黑名单"),
    Option("黑名单 解除|移出|移除", dest="remove", help_text="将当前群组移出黑名单"),
    Option("退出"),
    Option("检查"),
    Option("列出"),
    meta=CommandMeta("操作当前群组", example="$群管 当前状态\n$群管 黑名单 加入"),
)


@alcommand(Alconna("调试", meta=CommandMeta("显示调试信息")))
@permission("admin")
async def debug(app: Ariadne, sender: Sender, bot: RaianBotInterface):
    md = f"""\
# {bot.config.bot_name} 调试信息

## 统计

- 当前共加载模块: {len(it(Saya).channels)}个

- 当前共加入群:   {len(bot.data.groups)}个

- 当前共有:      {len(bot.data.users)}人参与签到
"""
    if bot.config.plugin.disabled:
        md += "\n- 已禁用模块: \n  - " + "\n  - ".join(bot.config.plugin.disabled) + "\n"
    if isinstance(sender, Group):
        md += f"## {sender.name} 相关:\n\n"
        group = bot.data.get_group(sender.id)
        md += "- 所在群组已列入黑名单\n\n" if group.in_blacklist else "- 所在群组未列入黑名单\n"
        if group.disabled:
            md += "\n- 所在群组已禁用功能: \n  - " + "\n  - ".join(group.disabled) + "\n"
    return await app.send_message(
        sender,
        MessageChain(Image(data_bytes=await create_md(md, width=360, height=(md.count("\n") + 5) * 16))),
    )


@alcommand(module_control, send_error=True)
@assign("列出")
async def _m_list(app: Ariadne, sender: Sender, bot: RaianBotInterface):
    saya = it(Saya)
    md = f"""\
<div align="center">

# {bot.config.bot_name} 模块信息

| 模块名 | 模块路径 | 状态 |
| ----- | ------- | --- |
"""
    for path, channel in saya.channels.items():
        md += f"| {channel.meta['name'] or path.split('.')[-1]} | {path} | ✔ 已安装 |\n"
    for path in bot.config.plugin.disabled:
        md += f"| {path.split('.')[-1]} | {path} | ❌ 已卸载 |\n"
    return await app.send_message(sender, MessageChain(Image(data_bytes=await MarkdownToImg().render(md))))


@alcommand(module_control, send_error=True)
@permission("master")
@assign("卸载")
async def _m_uninstall(app: Ariadne, sender: Sender, path: Match[str], bot: RaianBotInterface):
    saya = it(Saya)
    channel_path = path.result if path.available else "admin"
    if channel_path.split(".")[-1] == "admin":
        return await app.send_message(sender, MessageChain("无法卸载管理模块"))
    if len(channel_path.split(".")) <= 1:
        for root in bot.config.plugin.paths:
            if f"{root}.{channel_path}" in saya.channels:
                channel_path = f"{root}.{channel_path}"
                break
    if not (_channel := saya.channels.get(channel_path)):
        return await app.send_message(sender, MessageChain("该模组未安装, 您可能需要安装它"))
    try:
        saya.uninstall_channel(_channel)
    except Exception as e:
        await app.send_message(sender, MessageChain(f"卸载 {channel_path} 失败！"))
        raise e
    else:
        bot.config.plugin.disabled.append(channel_path)
        return await app.send_message(sender, MessageChain(f"卸载 {channel_path} 成功"))


@alcommand(module_control, send_error=True)
@permission("master")
@assign("安装")
async def _m_install(app: Ariadne, sender: Sender, path: Match[str], bot: RaianBotService):
    saya = it(Saya)
    channel_path = path.result if path.available else "admin"
    if channel_path.split(".")[-1] == "admin":
        return
    if len(channel_path.split(".")) <= 1:
        for root in bot.config.plugin.paths:
            if Path(f"./{root}/{channel_path}.py").exists():
                channel_path = f"{root}.{channel_path}"
                break
    if channel_path in saya.channels and channel_path not in bot.config.plugin.disabled:
        return await app.send_message(sender, MessageChain("该模组已安装"))
    try:
        with bot.context.use(bot):
            with saya.module_context():
                saya.require(channel_path)
    except Exception as e:
        await app.send_message(sender, MessageChain(f"安装 {channel_path} 失败！"))
        raise e
    else:
        if channel_path in bot.config.plugin.disabled:
            bot.config.plugin.disabled.remove(channel_path)
        return await app.send_message(sender, MessageChain(f"安装 {channel_path} 成功"))


@alcommand(module_control, send_error=True)
@permission("master")
@assign("重载")
async def _m_reload(app: Ariadne, sender: Sender, path: Match[str], bot: RaianBotService):
    saya = it(Saya)
    channel_path = path.result if path.available else "admin"
    if channel_path.split(".")[-1] == "admin":
        return
    if len(channel_path.split(".")) <= 1:
        for root in bot.config.plugin.paths:
            if Path(f"./{root}/{channel_path}.py").exists():
                channel_path = f"{root}.{channel_path}"
                break
    if not (_channel := saya.channels.get(channel_path)):
        return await app.send_message(sender, MessageChain("该模组未安装, 您可能需要安装它"))
    try:
        saya.uninstall_channel(_channel)
    except Exception as e:
        await app.send_message(sender, MessageChain(f"重载 {channel_path} 过程中卸载失败！"))
        raise e
    try:
        with bot.context.use(bot):
            with saya.module_context():
                saya.require(channel_path)
    except Exception as e:
        await app.send_message(sender, MessageChain(f"重载 {channel_path} 过程中安装失败！"))
        raise e
    else:
        return await app.send_message(sender, MessageChain(f"重载 {channel_path} 成功"))


@alcommand(module_control, send_error=True)
@assign("$main")
async def _m_main(app: Ariadne, sender: Sender):
    return await app.send_message(sender, await send_handler(module_control.get_help()))


@alcommand(function_control, send_error=True)
@assign("$main")
async def _f_main(app: Ariadne, sender: Sender):
    return await app.send_message(sender, await send_handler(function_control.get_help()))


@alcommand(function_control, private=False, send_error=True)
@assign("列出")
async def _f_list(app: Ariadne, sender: Group, bot: RaianBotInterface):
    group = bot.data.get_group(sender.id)
    md = f"""\
<div align="center">

# {bot.config.bot_name} 功能概览

## {sender.name} / {sender.id} 统计情况

| 名称 | 状态 | 功能备注 |
| ----- | ------- | --- |
"""
    for i in bot.data.funcs:
        stat = "❌ 禁用" if i in group.disabled else "🚫 黑名单" if group.in_blacklist else "✔ 启用"
        md += (
            f"| {i} | {stat} | {bot.data.func_description(i)}{'(默认禁用)' if i in bot.data.disable_functions else ''} |\n"
        )
    return await app.send_message(sender, MessageChain(Image(data_bytes=(await MarkdownToImg().render(md)))))


@alcommand(function_control, private=False, send_error=True)
@permission("admin")
@assign("启用")
async def _f_active(app: Ariadne, sender: Group, name: Match[str], bot: RaianBotInterface):
    group = bot.data.get_group(sender.id)
    if not name.available:
        return await app.send_message(sender, MessageChain("该功能未找到"))
    if group.in_blacklist or sender.id in bot.data.cache["blacklist"]:
        return await app.send_message(sender, MessageChain("所在群组已进入黑名单, 设置无效"))
    if name.result not in bot.data.funcs:
        return await app.send_message(sender, MessageChain(f"功能 {name.result} 不存在"))
    if name.result not in group.disabled:
        return await app.send_message(sender, MessageChain(f"功能 {name.result} 未禁用"))
    group.disabled.remove(name.result)
    bot.data.update_group(group)
    return await app.send_message(sender, MessageChain(f"功能 {name.result} 启用成功"))


@alcommand(function_control, private=False, send_error=True)
@permission("admin")
@assign("禁用")
async def _f(app: Ariadne, sender: Group, name: Match[str], bot: RaianBotInterface):
    group = bot.data.get_group(sender.id)
    if not name.available:
        return await app.send_message(sender, MessageChain("该功能未找到"))
    if group.in_blacklist or sender.id in bot.data.cache["blacklist"]:
        return await app.send_message(sender, MessageChain("所在群组已进入黑名单, 设置无效"))
    if name.result not in bot.data.funcs:
        return await app.send_message(sender, MessageChain(f"功能 {name.result} 不存在"))
    if name.result in group.disabled:
        return await app.send_message(sender, MessageChain(f"功能 {name.result} 已经禁用"))
    group.disabled.append(name.result)
    bot.data.update_group(group)
    return await app.send_message(sender, MessageChain(f"功能 {name.result} 禁用成功"))


@alcommand(group_control, send_error=True)
@assign("$main")
async def _g_main(app: Ariadne, sender: Sender):
    return await app.send_message(sender, await send_handler(group_control.get_help()))


@alcommand(group_control, private=False, send_error=True)
@permission("admin")
@assign("退出")
async def _g_quit(app: Ariadne, sender: Group, bot: RaianBotInterface):
    await app.send_message(sender, "正在退出该群聊。。。")
    logger.debug(f"quiting from {sender.name}({sender.id})...")
    bot.data.remove_group(sender.id)
    return await app.quit_group(sender)


@alcommand(group_control, private=False, send_error=True)
@assign("status")
async def _g_state(app: Ariadne, sender: Group, bot: RaianBotInterface):
    group = bot.data.get_group(sender.id)
    fns = "所在群组已列入黑名单" if group.in_blacklist else f"所在群组已禁用功能: {group.disabled}"
    return await app.send_message(sender, fns)


@alcommand(group_control, send_error=True)
@permission("admin")
@assign("检查")
async def _g_check(app: Ariadne, sender: Sender, bot: RaianBotInterface):
    groups = [i.id for i in await app.get_group_list()]
    moved = [gid for gid in bot.data.groups if int(gid) not in groups]
    if not moved:
        return await app.send_message(sender, "自检完成。未发现失效群组")
    for gid in moved:
        bot.data.remove_group(int(gid))
    bot.data.cache["all_joined_group"] = [int(i) for i in bot.data.groups]
    return await app.send_message(sender, f"检测出失效群组：\n" + "\n".join(moved))


@alcommand(group_control, send_error=True)
@permission("admin")
@assign("列出")
async def _g_list(app: Ariadne, sender: Sender, bot: RaianBotInterface):
    groups: List[Group] = await app.get_group_list()
    for i in range(1 + (len(groups) - 1) // 50):
        select = groups[i * 50: (i + 1) * 50]
        forwards = []
        now = datetime.now()
        for gp in select:
            async with app.service.client_session.get(f"https://p.qlogo.cn/gh/{gp.id}/{gp.id}/") as resp:
                data = await resp.read()
            gp_name = "".join(i for i in gp.name if is_chinese(i) or 31 < ord(i) < 127)
            gp_name = re.sub(r"<\$[^<>]*?>", "", gp_name)
            forwards.append(
                ForwardNode(
                    target=bot.config.mirai.account,
                    name=bot.config.bot_name,
                    time=now,
                    message=MessageChain(Image(data_bytes=data), f"\n{gp_name}({gp.id})"),
                )
            )
        if not forwards:
            return await app.send_message(sender, MessageChain("该 bot 未加入任意群组"))
        await app.send_message(sender, MessageChain(Forward(*forwards)))


@alcommand(group_control, private=False, send_error=True)
@permission("admin")
@assign("add")
async def _g_bl_add(app: Ariadne, sender: Group, bot: RaianBotInterface):
    group = bot.data.get_group(sender.id)
    if group.in_blacklist or sender.id in bot.data.cache["blacklist"]:
        return await app.send_message(sender, "该群组已加入黑名单!")
    group.in_blacklist = True
    bot.data.update_group(group)
    bot.data.cache["blacklist"].append(sender.id)
    return await app.send_message(sender, "该群组列入黑名单成功!")


@alcommand(group_control, private=False, send_error=True)
@permission("admin")
@assign("remove")
async def _g_bl_remove(app: Ariadne, sender: Group, bot: RaianBotInterface):
    group = bot.data.get_group(sender.id)
    if group.in_blacklist or sender.id in bot.data.cache["blacklist"]:
        group.in_blacklist = False
        bot.data.update_group(group)
        if sender.id in bot.data.cache["blacklist"]:
            bot.data.cache["blacklist"].remove(sender.id)
        return await app.send_message(sender, "该群组移出黑名单成功!")
    return await app.send_message(sender, "该群组未列入黑名单!")
