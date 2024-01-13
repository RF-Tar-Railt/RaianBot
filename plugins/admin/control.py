from __future__ import annotations

from pathlib import Path
from secrets import token_hex

from arclet.alconna import Alconna, Args, Arparma, CommandMeta, Field, MultiVar, Option
from arclet.alconna.graia import Match, alcommand, assign
from avilla.core import Context, Picture, RawResource
from avilla.qqapi.exception import ActionFailed
from creart import it
from graia.saya import Saya
from sqlalchemy import select

from app.config import BotConfig, extract_plugin_config
from app.core import RaianBotService
from app.database import DatabaseService, Group
from app.image import md2img
from app.shortcut import exclusive, permission, picture
from app.statistic import Statistic

module_control = Alconna(
    "模块",
    Option("列出", alias=["list"]),
    Option(
        "禁用",
        Args["path", str, Field(completion=lambda: "试试用‘admin’")],
        alias=["disable"],
        help_text="禁用一个模块",
    ),
    Option(
        "启用",
        Args["path", str, Field(completion=lambda: "试试用‘admin’")],
        alias=["enable"],
        help_text="启用一个模块",
    ),
    Option(
        "重载",
        Args["path", str, Field(completion=lambda: "试试用‘admin’")],
        alias=["重启", "reload"],
        help_text="重新载入一个模块",
    ),
    meta=CommandMeta("管理机器人的模块", example="$模块 列出\n$模块 卸载 setu", extra={"supports": {"mirai", "qqapi"}}),
)

function_control = Alconna(
    "功能",
    Option("列出", alias=["list"]),
    Option(
        "禁用",
        Args["names", MultiVar(str), Field(completion=lambda: "试试用‘greet’")],
        alias=["ban", "disable"],
        help_text="禁用功能",
    ),
    Option(
        "启用",
        Args["names", MultiVar(str), Field(completion=lambda: "试试用‘greet’")],
        alias=["active"],
        help_text="启用功能",
    ),
    Option(
        "保留",
        Args["names", MultiVar(str), Field(completion=lambda: "试试用‘greet’")],
        alias=["reserve"],
        help_text="保留功能，禁用除此之外的所有功能",
    ),
    Option("清空", alias=["clear"], help_text="清空所有被禁用功能"),
    meta=CommandMeta(
        "管理机器人的功能",
        usage="可传入多个功能名, 以空格分隔",
        example="$功能 列出\n$功能 禁用 greet",
        extra={"supports": {"mirai", "qqapi"}},
    ),
)

function_control.shortcut(
    "禁用敏感功能",
    prefix=True,
    command="功能 禁用 member_join member_leave ai",
)

blacklist_control = Alconna(
    "黑名单",
    Option("检查", dest="status", help_text="查看当前群组是否在黑名单中"),
    Option("列入|加入", dest="add", help_text="将当前群组加入黑名单"),
    Option("解除|移出|移除", dest="remove", help_text="将当前群组移出黑名单"),
    meta=CommandMeta("管理群组黑名单", example="黑名单 检查\n$黑名单 加入", extra={"supports": {"mirai", "qqapi"}}),
)


@alcommand(module_control, post=True, send_error=True)
@assign("列出")
@exclusive
async def _m_list(ctx: Context, bot: RaianBotService, conf: BotConfig):
    saya = it(Saya)
    md = f"""\
<div align="center">

# {conf.name} ({conf.account}) 模块信息

| 模块名 | 模块路径 | 状态 |
| ----- | ------- | --- |
"""
    for path, channel in saya.channels.items():
        md += f"| {channel.meta.get('name') or path.split('.')[-2]} | {path} | ✔ 已安装 |\n"
    for path in bot.config.plugin.disabled:
        if path not in saya.channels:
            md += f"| {path.split('.')[-2]} | {path} | ❌ 已卸载 |\n"
        else:
            md += f"| {path.split('.')[-2]} | {path} | ❌ 已禁用 |\n"
    img = await md2img(md)
    try:
        await ctx.scene.send_message(Picture(RawResource(img)))
        return Statistic("模块", ctx.scene.channel, ctx.client.user)
    except Exception:
        url = await bot.upload_to_cos(img, f"module_list_{token_hex(16)}.jpg")
        try:
            await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            await ctx.scene.send_message("模块列表：\n" + "\n".join(saya.channels.keys()))
        return Statistic("模块", ctx.scene.channel, ctx.client.user)


@alcommand(module_control, post=True, send_error=True)
@permission("master")
@assign("重载")
@exclusive
async def _m_reload(ctx: Context, path: Match[str], bot: RaianBotService):
    saya = it(Saya)
    channel_path = path.result if path.available else "plugins.admin"
    if channel_path.split(".")[-1] == "admin":
        return
    parts = channel_path.split(".")
    if len(parts) <= 1:
        for root in bot.config.plugin.paths:
            if Path(f"./{root}/{channel_path}/main.py").exists():
                parts.insert(0, root)
                break
    _path, name = parts[0], parts[-1]
    if not (_channel := saya.channels.get(f"{_path}.{name}.main")):
        with saya.module_context():
            if model := extract_plugin_config(bot.config, _path, name):
                bot.config.plugin.configs[type(model)] = model
            saya.require(f"{_path}.{name}.main")
        await ctx.scene.send_message(f"重载 {_path}.{name} 成功")
        return Statistic("模块", ctx.scene.channel, ctx.client.user)
    try:
        saya.uninstall_channel(_channel)
    except Exception as e:
        await ctx.scene.send_message(f"重载 {_path}.{name} 过程中卸载失败！\n{e}\n请修改后重试")
        raise e
    try:
        with saya.module_context():
            if model := extract_plugin_config(bot.config, _path, name):
                bot.config.plugin.configs[type(model)] = model
            saya.require(f"{_path}.{name}.main")
    except Exception as e:
        await ctx.scene.send_message(f"重载 {_path}.{name} 过程中安装失败！\n{e}\n请修改后重试")
        raise e
    else:
        await ctx.scene.send_message(f"重载 {_path}.{name} 成功")
        return Statistic("模块", ctx.scene.channel, ctx.client.user)


@alcommand(module_control, post=True, send_error=True)
@assign("$main")
@exclusive
async def _m_main(ctx: Context):
    await ctx.scene.send_message(
        """\
模块管理
- 列出：列出所有已安装模块
- 禁用：禁用一个模块
- 启用：启用一个模块
- 重载：重载一个模块
"""
    )
    return Statistic("模块", ctx.scene.channel, ctx.client.user)


@alcommand(module_control, post=True, send_error=True)
@permission("master")
@assign("启用")
@exclusive
async def _m_enable(ctx: Context, path: Match[str], bot: RaianBotService):
    saya = it(Saya)
    channel_path = path.result if path.available else "plugins.admin"
    if channel_path.split(".")[-1] == "admin":
        return
    parts = channel_path.split(".")
    if len(parts) <= 1:
        for root in bot.config.plugin.paths:
            if Path(f"./{root}/{channel_path}/main.py").exists():
                parts.insert(0, root)
                break
    _path, name = parts[0], parts[-1]
    if not (_channel := saya.channels.get(f"{_path}.{name}.main")):
        return await ctx.scene.send_message("该模组未安装, 您可能需要安装它")
    if f"{_path}.{name}" in bot.config.plugin.disabled:
        bot.config.plugin.disabled.remove(f"{_path}.{name}")
        await ctx.scene.send_message(f"启用 {_path}.{name} 成功")
        return Statistic("模块", ctx.scene.channel, ctx.client.user)
    return await ctx.scene.send_message("该模组已启用")


@alcommand(module_control, post=True, send_error=True)
@permission("master")
@assign("禁用")
@exclusive
async def _m_disable(ctx: Context, path: Match[str], bot: RaianBotService):
    saya = it(Saya)
    channel_path = path.result if path.available else "plugins.admin"
    if channel_path.split(".")[-1] == "admin":
        return
    parts = channel_path.split(".")
    if len(parts) <= 1:
        for root in bot.config.plugin.paths:
            if Path(f"./{root}/{channel_path}/main.py").exists():
                parts.insert(0, root)
                break
    _path, name = parts[0], parts[-1]
    if not (_channel := saya.channels.get(f"{_path}.{name}.main")):
        return await ctx.scene.send_message("该模组未安装, 您可能需要安装它")
    if f"{_path}.{name}" in bot.config.plugin.disabled:
        return await ctx.scene.send_message("该模组已被禁用")
    bot.config.plugin.disabled.append(f"{_path}.{name}")
    await ctx.scene.send_message(f"禁用 {_path}.{name} 成功")
    return Statistic("模块", ctx.scene.channel, ctx.client.user)


@alcommand(function_control, post=True, send_error=True)
@assign("$main")
@exclusive
async def _f_main(ctx: Context):
    await ctx.scene.send_message(
        """\
功能管理
- 列出：列出所有已安装功能
- 禁用：禁用功能
- 启用：启用功能
- 保留：保留功能，禁用除此之外的所有
- 清空：清空所有被禁用功能
"""
    )
    return Statistic("功能", ctx.scene.channel, ctx.client.user)


@alcommand(function_control, post=True, send_error=True)
@assign("列出")
@exclusive
async def _f_list(ctx: Context, bot: RaianBotService, db: DatabaseService, conf: BotConfig):
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
        if not group:
            return await ctx.scene.send_message("请在群组内使用该命令")
    md = f"""\
<div align="center">

# {conf.name} ({conf.account}) 功能概览

## {ctx.scene.channel} 统计情况

| 名称 | 状态 | 功能备注 |
| ----- | ------- | --- |
"""
    for i in bot.functions.keys():
        stat = "❌ 禁用" if i in group.disabled else "🚫 黑名单" if group.in_blacklist else "✔ 启用"
        md += f"| {i} | {stat} | {bot.func_description(i)}{' (默认禁用)' if i in bot.disabled else ''} |\n"
    img = await md2img(md)
    try:
        await ctx.scene.send_message(Picture(RawResource(img)))
        return Statistic("功能", ctx.scene.channel, ctx.client.user)
    except Exception:
        url = await bot.upload_to_cos(img, f"func_list_{token_hex(16)}.jpg")
        try:
            await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            await ctx.scene.send_message("功能列表：\n" + "\n".join(bot.functions.keys()))
        return Statistic("功能", ctx.scene.channel, ctx.client.user)


@alcommand(function_control, post=True, send_error=True)
@permission("admin")
@assign("启用")
@exclusive
async def _f_active(ctx: Context, arp: Arparma, bot: RaianBotService, db: DatabaseService):
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
        if not group:
            return await ctx.scene.send_message("请在群组内使用该命令")
        if group.in_blacklist:
            return await ctx.scene.send_message("所在群组已进入黑名单, 设置无效")
        names = arp.query[tuple[str, ...]]("names")
        for name in names:
            if name not in bot.functions:
                return await ctx.scene.send_message(f"功能 {name} 不存在")
            if name not in group.disabled:
                return await ctx.scene.send_message(f"功能 {name} 未禁用")
            group.disabled = [i for i in group.disabled if i != name]
            await session.commit()
            await session.refresh(group)
        await ctx.scene.send_message(f"功能 {', '.join(names)} 启用成功")
        return Statistic("功能", ctx.scene.channel, ctx.client.user)


@alcommand(function_control, post=True, send_error=True)
@permission("admin")
@assign("禁用")
@exclusive
async def _f(ctx: Context, arp: Arparma, bot: RaianBotService, db: DatabaseService):
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
        if not group:
            return await ctx.scene.send_message("请在群组内使用该命令")
        if group.in_blacklist:
            return await ctx.scene.send_message("所在群组已进入黑名单, 设置无效")
        names = arp.query[tuple[str, ...]]("names")
        for name in names:
            if name not in bot.functions:
                return await ctx.scene.send_message(f"功能 {name} 不存在")
            if name in group.disabled:
                return await ctx.scene.send_message(f"功能 {name} 已经禁用")
            group.disabled = [*group.disabled, name]
            await session.commit()
            await session.refresh(group)
        await ctx.scene.send_message(f"功能 {', '.join(names)} 禁用成功")
        return Statistic("功能", ctx.scene.channel, ctx.client.user)


@alcommand(function_control, post=True, send_error=True)
@permission("admin")
@assign("保留")
@exclusive
async def _f_reserve(ctx: Context, arp: Arparma, bot: RaianBotService, db: DatabaseService):
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
        if not group:
            return await ctx.scene.send_message("请在群组内使用该命令")
        if group.in_blacklist:
            return await ctx.scene.send_message("所在群组已进入黑名单, 设置无效")
        names = arp.query[tuple[str, ...]]("names")
        group.disabled = [i for i in bot.functions.keys() if i not in names]
        await session.commit()
        await session.refresh(group)
        await ctx.scene.send_message(f"功能 {', '.join(names)} 保留成功")
        return Statistic("功能", ctx.scene.channel, ctx.client.user)


@alcommand(function_control, post=True, send_error=True)
@permission("admin")
@assign("清空")
@exclusive
async def _f_clear(ctx: Context, db: DatabaseService):
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
        if not group:
            return await ctx.scene.send_message("请在群组内使用该命令")
        if group.in_blacklist:
            return await ctx.scene.send_message("所在群组已进入黑名单, 设置无效")
        group.disabled = []
        await session.commit()
        await session.refresh(group)
        await ctx.scene.send_message("成功清空所有被禁用功能!")
        return Statistic("功能", ctx.scene.channel, ctx.client.user)


@alcommand(blacklist_control, post=True, send_error=True)
@assign("$main")
@exclusive
async def _bl_main(ctx: Context):
    await ctx.scene.send_message(
        """\
黑名单管理
- 检查：查看当前群组是否在黑名单中
- 加入：将当前群组加入黑名单
- 移出：将当前群组移出黑名单
"""
    )
    return Statistic("黑名单", ctx.scene.channel, ctx.client.user)


@alcommand(blacklist_control, post=False, send_error=True)
@assign("status")
@exclusive
async def _bl_state(ctx: Context, db: DatabaseService):
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
        if not group:
            return await ctx.scene.send_message("请在群组内使用该命令")
        if group.in_blacklist:
            await ctx.scene.send_message("所在群组已进入黑名单")
        else:
            await ctx.scene.send_message(f"所在群组已禁用功能: {group.disabled}")
        return Statistic("黑名单", ctx.scene.channel, ctx.client.user)


@alcommand(blacklist_control, post=True, send_error=True)
@permission("admin")
@assign("add")
@exclusive
async def _bl_add(ctx: Context, db: DatabaseService):
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
        if not group:
            return await ctx.scene.send_message("请在群组内使用该命令")
        if group.in_blacklist:
            return await ctx.scene.send_message("所在群组已进入黑名单")
        group.in_blacklist = True
        await session.commit()
        await ctx.scene.send_message("该群组列入黑名单成功!")
        return Statistic("黑名单", ctx.scene.channel, ctx.client.user)


@alcommand(blacklist_control, post=True, send_error=True)
@permission("admin")
@assign("remove")
@exclusive
async def _bl_remove(ctx: Context, db: DatabaseService):
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
        if not group:
            return await ctx.scene.send_message("请在群组内使用该命令")
        if not group.in_blacklist:
            return await ctx.scene.send_message("所在群组未进入黑名单")
        group.in_blacklist = False
        await session.commit()
        await ctx.scene.send_message("该群组移出黑名单成功!")
        return Statistic("黑名单", ctx.scene.channel, ctx.client.user)
