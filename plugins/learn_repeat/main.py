import re
from datetime import datetime
from typing import Union
from arclet.alconna import Alconna, Args, Option, AllParam, Arparma, CommandMeta
from arclet.alconna.graia import alcommand, assign, Match
from avilla.core import Context, MessageChain, MessageReceived, Notice, Selector
from graia.broadcast.exceptions import PropagationCancelled
from avilla.standard.qq.elements import Forward, Node
from avilla.standard.core.profile import Nick
from avilla.qqapi.account import QQAPIAccount

from graia.saya.builtins.broadcast.shortcut import listen, priority
from sqlalchemy import Select

from app.core import RaianBotService
from app.database import DatabaseService
from app.message import deserialize_message, serialize_message
from app.shortcut import accessable, exclusive, record

from .model import Learn

bot = RaianBotService.current()

repeat = Alconna(
    [""],
    "学习回复",
    Option("增加", Args["name", str]["content", AllParam], help_text="增加一条学习记录"),
    Option("修改", Args["name", str]["content", AllParam], help_text="修改一条已存在的学习记录"),
    Option("删除", Args["target", [str, Notice]], help_text="删除一条学习记录, 若at用户则删除该用户的所有学习记录"),
    Option("查找", Args["target", str], help_text="查找是否有指定的学习记录"),
    Option("列出", Args["target?", Notice], help_text="列出该群所有的学习记录, 若at用户则列出该用户的所有学习记录"),
    meta=CommandMeta("让机器人记录指定内容并尝试回复", usage="注意: 该命令不需要 “渊白” 开头", example="学习回复 增加 abcd xyz", extra={"supports": {"mirai", "qqapi"}}),
)

image_path = bot.config.plugin_data_dir / 'learn_repeat'
# base_path.mkdir(parents=True, exist_ok=True)
# image_path = base_path / "image"
image_path.mkdir(exist_ok=True)


@alcommand(repeat, post=True, send_error=True)
@assign("$main")
@exclusive
@accessable
async def shelp(ctx: Context):
    return await ctx.scene.send_message(
        "[Repeat] 该命令用以让机器人记录指定内容并尝试回复\n"
        "命令用法：\n"
        "学习回复 增加 (记录名) (内容)：增加一条学习记录\n"
        "学习回复 修改 (记录名) (内容)：修改一条已存在的学习记录\n"
        "学习回复 删除 (记录名/at用户)：删除一条学习记录\n"
        "学习回复 查找 (记录名)：查找是否有指定的学习记录\n"
        "学习回复 列出 [at用户]：列出该群所有的学习记录\n"
    )


@alcommand(repeat, post=True, send_error=True)
@assign("列出")
@exclusive
@accessable
async def rlist(ctx: Context, target: Match[Notice], db: DatabaseService):
    async with db.get_session() as session:
        records = (await session.scalars(Select(Learn).where(Learn.id == ctx.scene.channel))).all()
    if not records:
        return await ctx.scene.send_message("该群未找到任何学习记录")
    if target.available:
        _target = target.result.target
        records = [rec for rec in records if rec.author == _target.display_without_land]
        if not records:
            return await ctx.scene.send_message("呜, 找不到这个人的记录")
    _data = {rec.key: rec for rec in records}
    keys = [rec.key for rec in records]
    if isinstance(ctx.account, QQAPIAccount):
        return await ctx.scene.send_message("\n".join(keys))
    for i in range(1 + (len(keys) - 1) // 50):
        selected = keys[i * 50: (i + 1) * 50]
        forwards = []
        now = datetime.now()
        for key in selected:
            rec = _data[key]
            author = Selector.from_follows_pattern(f"land(qq).{rec.author}")
            try:
                nick = await ctx.pull(Nick, author)
                name = nick.nickname or nick.name
            except Exception:
                name = author.last_value
            content = deserialize_message(rec.content)
            forwards.append(
                Node(name=name, uid=author.last_value, time=now, content=f"{key}:\n" + content)
            )
        await ctx.scene.send_message(Forward(*forwards))


@alcommand(repeat, post=True, send_error=True)
@assign("查找")
@exclusive
@accessable
async def rfind(ctx: Context, target: Match[str], db: DatabaseService):
    async with db.get_session() as session:
        rec = (
            await session.scalars(
                Select(Learn)
                .where(Learn.id == ctx.scene.channel)
                .where(Learn.key == target.result)
            )
        ).one_or_none()
    if not rec:
        return await ctx.scene.send_message("查找失败！")
    content = deserialize_message(rec.content)
    return await ctx.scene.send_message("查找成功！\n内容为:\n" + content)


@alcommand(repeat, post=True, send_error=True)
@assign("删除")
@exclusive
@accessable
async def rremove(ctx: Context, db: DatabaseService, target: Match[Union[str, Notice]]):
    async with db.get_session() as session:
        records = (await session.scalars(Select(Learn).where(Learn.id == ctx.scene.channel))).all()
        if not records:
            return await ctx.scene.send_message("该群未找到任何学习记录")
        if isinstance(target.result, Notice):
            _target = target.result.target
            records = [rec for rec in records if rec.author == _target.display_without_land]
            if not records:
                return await ctx.scene.send_message("呜, 找不到这个人的记录")
        else:
            records = [rec for rec in records if rec.key == target.result]
            if not records:
                return await ctx.scene.send_message("呜, 找不到这条记录")
            for row in records:
                await session.delete(row)
            await session.commit()
    return await ctx.scene.send_message("删除记录成功了！")


@alcommand(repeat, private=False, send_error=True)
@assign("增加")
@exclusive
@accessable
async def radd(ctx: Context, name: Match[str], result: Arparma, db: DatabaseService):
    content = result.query[MessageChain]("增加.content")
    if not content:
        return await ctx.scene.send_message("喂, 没有内容啊~")
    serialized = await serialize_message(content, ctx, image_path)
    if not serialized:
        return await ctx.scene.send_message("喂, 没有内容啊~")
    if name.result in {"(.+?)", ".+?", ".*?", "(.*?)", ".+", ".*", "."}:
        return await ctx.scene.send_message("关键词过于宽泛！")
    key = name.result.replace("**", "*")
    if len(key) > 256:
        return await ctx.scene.send_message("关键词过长！")
    async with db.get_session() as session:
        rec = Learn(id=ctx.scene.channel, key=key, author=ctx.client.display_without_land, content=serialized)
        session.add(rec)
        await session.commit()
    return await ctx.scene.send_message("我学会了！你现在可以来问我了！")


@alcommand(repeat, private=False, send_error=True)
@assign("修改")
@exclusive
@accessable
async def redit(ctx: Context, name: Match[str], result: Arparma, db: DatabaseService):
    content = result.query[MessageChain]("修改.content")
    if not content:
        return await ctx.scene.send_message("喂, 没有内容啊~")
    serialized = await serialize_message(content, ctx, image_path)
    if not serialized:
        return await ctx.scene.send_message("喂, 没有内容啊~")
    async with db.get_session() as session:
        rec = (
            await session.scalars(
                Select(Learn)
                .where(Learn.id == ctx.scene.channel)
                .where(Learn.key == name.result)
            )
        ).one_or_none()
        if not rec:
            return await ctx.scene.send_message("呜, 找不到这条记录")
        rec.content = serialized
        await session.commit()
    return await ctx.scene.send_message("我学会了！你现在可以来问我了！")


@listen(MessageReceived)
@priority(17)
@record("repeat")
async def handle(ctx: Context, message: MessageChain, db: DatabaseService):
    """依据记录回复对应内容"""
    async with db.get_session() as session:
        records = (await session.scalars(Select(Learn).where(Learn.id == ctx.scene.channel))).all()
        if not records:
            return
        for rec in records:
            if re.fullmatch(rec.key, str(message.exclude(Notice)).lstrip()):
                content = deserialize_message(rec.content)
                await ctx.scene.send_message(content)
                raise PropagationCancelled
