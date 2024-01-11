from __future__ import annotations

from arclet.alconna.graia import startswith
from avilla.core import Context, Notice
from avilla.core.event import SceneCreated, SceneDestroyed
from avilla.elizabeth.account import ElizabethAccount
from avilla.standard.core.message import MessageReceived
from avilla.standard.core.privilege import Privilege
from graia.amnesia.message import MessageChain
from graia.saya.builtins.broadcast.shortcut import listen, priority
from sqlalchemy import select

from app.config import BotConfig
from app.core import RaianBotService
from app.database import DatabaseService, Group
from app.shortcut import allow

from . import control  # noqa: F401
from . import debug  # noqa: F401
from . import exception  # noqa: F401
from . import member  # noqa: F401
from . import request  # noqa: F401
from .model import BlacklistCache


@listen(MessageReceived)
@startswith("清理失效群")
@priority(6)
async def _init_f(ctx: Context, db: DatabaseService, bot: RaianBotService, conf: BotConfig):
    if ctx.client.user != conf.master_id:
        return
    groups = set()
    async for group in ctx.query("land.group"):
        groups.add(group.pattern["group"])
    async with db.get_session() as session:
        gps = (
            await session.scalars(
                select(Group)
                .where(Group.platform == "qq")
                .where(Group.accounts == [ctx.account.route.display])
                .where(Group.id.notin_(groups))
            )
        ).all()
        for gp in gps:
            await session.delete(gp)
        await session.commit()
    await ctx.account.get_context(conf.master()).scene.send_message(f"已清理失效群聊，共清理 {len(gps)} 个群聊")


@listen(MessageReceived, SceneCreated)
@priority(7)
async def _init_g(ctx: Context, db: DatabaseService, bot: RaianBotService):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return
    if ctx.scene.follows("::guild"):
        return
    account = ctx.account.route.display
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == ctx.scene.channel))).one_or_none()
        if not group:
            group = Group(
                id=ctx.scene.channel,
                platform="qq" if isinstance(ctx.account, ElizabethAccount) else "qqapi",
                accounts=[account],
                disabled=list(bot.disabled),
            )
            session.add(group)
            await session.commit()
            await session.refresh(group)
        elif account not in group.accounts:
            group.accounts = [*group.accounts, account]
            await session.commit()
            await session.refresh(group)


@listen(SceneCreated)
@priority(8)
@allow(ElizabethAccount)
async def introduce(ctx: Context, bot: RaianBotService, conf: BotConfig, db: DatabaseService):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return
    if not isinstance(ctx.account, ElizabethAccount):
        return
    group_id = ctx.scene.channel
    await ctx.account.get_context(conf.master()).scene.send_message(
        "收到加入群聊事件\n" f"群号：{group_id}\n" f"群名：{(await ctx.scene.summary()).name}\n"
    )
    await ctx.scene.send_message(
        f"我是 {conf.master_id} 的机器人 {conf.name}\n"
        f"如果有需要可以联系主人 {conf.master_id}，\n"
        f"尝试发送 {bot.config.command.headers[0]}帮助 以查看功能列表\n"
        "项目地址：https://github.com/RF-Tar-Railt/RaianBot\n"
        "赞助（爱发电）：https://afdian.net/@rf_tar_railt\n"
        "机器人交流群：122680593",
    )
    ats = []
    async for _member in ctx.query(f"land.group({group_id}).member"):
        pri = await ctx.pull(Privilege, _member)
        if pri.available:
            ats.append(Notice(_member))
    await ctx.scene.send_message(
        MessageChain(
            [
                *ats,
                "\n管理员请注意："
                "\n本机器人默认开启如下功能："
                "\n - 入群提醒"
                "\n - 离群提醒"
                "\n - 禁言提醒"
                "\n - 解禁提醒"
                "\n - AI对话"
                "\n您可以使用"
                f"\n> {bot.config.command.headers[0]}功能 列出"
                f"\n> {bot.config.command.headers[0]}功能 禁用 <功能名>"
                f"\n> {bot.config.command.headers[0]}功能 启用 <功能名>"
                "\n来对机器人功能进行管理"
                "\n您也可以使用"
                f"> {bot.config.command.headers[0]}禁用敏感功能"
                "\n来禁用上述默认功能",
            ]
        )
    )
    async with db.get_session() as session:
        bl = (await session.scalars(select(BlacklistCache).where(BlacklistCache.id == group_id))).one_or_none()
        if bl and bl.in_blacklist:
            await ctx.scene.send_message(
                f"""\
检测到机器人曾被踢出该群聊
该群已列入机器人黑名单，禁用大部分功能
恢复使用请管理员输入命令 '{bot.config.command.headers[0]}黑名单 解除'
"""
            )
            group = (await session.scalars(select(Group).where(Group.id == group_id))).one_or_none()
            group.in_blacklist = True
            await session.delete(bl)
            await session.commit()


@listen(SceneDestroyed)
async def _remove(ctx: Context, db: DatabaseService, event: SceneDestroyed, conf: BotConfig):
    if ctx.scene.follows("::friend") or ctx.scene.follows("::guild.user"):
        return
    account = ctx.account.route.display
    group_id = ctx.scene.channel
    async with db.get_session() as session:
        group = (await session.scalars(select(Group).where(Group.id == group_id))).one_or_none()
        if group:
            if account in group.accounts:
                group.accounts = [i for i in group.accounts if i != account]
                await session.commit()
                await session.refresh(group)
            if not group.accounts:
                await session.delete(group)
                await session.commit()
        if event.active:
            return
        if not isinstance(ctx.account, ElizabethAccount):
            return
        if not event.indirect:
            bl = BlacklistCache(id=group_id, in_blacklist=True)
            await session.merge(bl)
            await session.commit()
            await ctx.account.get_context(conf.master()).scene.send_message(
                f"""\
收到被踢出群聊事件
群号：{group_id}
群名：{(await ctx.scene.nick()).name}
已添加至黑名单
"""
            )
        else:
            await ctx.account.get_context(conf.master()).scene.send_message(
                f"""\
收到群聊解散事件
群号：{group_id}
群名：{(await ctx.scene.nick()).name}
"""
            )
