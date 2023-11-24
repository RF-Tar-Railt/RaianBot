import asyncio
import re
from datetime import datetime
from secrets import token_hex

from arclet.alconna import Alconna, Args, CommandMeta, Option
from arclet.alconna.graia import Match, alcommand, assign
from avilla.core import ActionFailed, Avilla, Context, Picture, RawResource
from avilla.elizabeth.account import ElizabethAccount
from graia.scheduler.saya.shortcut import crontab
from sqlalchemy import select

from app.core import RaianBotService
from app.database import DatabaseService
from app.image import md2img
from app.shortcut import accessable, exclusive, picture, record
from library.sk_autosign import bind, sign

from .model import SKAutoSignRecord, SKAutoSignResultRecord

alc = Alconna(
    "森空岛签到",
    Option("绑定", Args["token", str], compact=True),
    Option("解除", compact=True),
    Option("查询", Args["uid?", str], compact=True),
    Option("方法"),
    meta=CommandMeta(
        "森空岛方舟自动签到",
        usage="""\
每天 0:30 开始自动签到，若与绑定者为好友则同时会私聊通知签到结果

**token获取方法**：在森空岛官网登录后，根据你的服务器，选择复制以下网址中的内容

官服：https://web-api.skland.com/account/info/hg

B服：https://web-api.skland.com/account/info/ak-b

***请在浏览器中获取token，避免在QQ打开的网页中获取，否则可能获取无效token***

再通过 ’渊白森空岛签到   绑定   你从网址里获取的token或者内容‘ 命令来绑定

**注意空格！！！**
""",
        example="""\
$森空岛签到方法
$绑定森空岛签到token1234
$森空岛签到绑定token1234
$解除森空岛签到
$森空岛签到结果
""",
        compact=True,
        extra={"supports": {"mirai", "qqapi"}},
    ),
)
alc.shortcut("绑定森空岛签到", {"command": "森空岛签到 绑定", "prefix": True})
alc.shortcut("解除森空岛签到", {"command": "森空岛签到 解除", "prefix": True})
alc.shortcut("森空岛签到结果", {"command": "森空岛签到 查询", "prefix": True})
alc.shortcut(r"(\d+)森空岛签到结果", {"command": "森空岛签到 查询 {0}", "prefix": True})

bot = RaianBotService.current()


@alcommand(alc)
@assign("方法")
@record("森空自动签到")
@exclusive
@accessable
async def notice(ctx: Context, db: DatabaseService):
    sender = ctx.client.last_value
    async with db.get_session() as session:
        _record = (await session.scalars(select(SKAutoSignRecord).where(SKAutoSignRecord.id == sender))).one_or_none()
        if not _record:
            img = await md2img(alc.meta.description)
            try:
                return await ctx.scene.send_message(Picture(RawResource(img)))
            except Exception:
                url = await bot.upload_to_cos(img, f"sk_autosign_{token_hex(16)}.jpg")
                try:
                    return await ctx.scene.send_message(picture(url, ctx))
                except ActionFailed:
                    return await ctx.scene.send_message(picture(url, ctx))
        ans = []
        async for resp in sign(_record):  # type: ignore
            if resp["status"]:
                res = SKAutoSignResultRecord(id=sender, uid=resp["target"], date=datetime.now(), result=resp)
                await session.merge(res)
                ans.append(resp["text"])
            await asyncio.sleep(1)
        await session.commit()
        await ctx.scene.send_message("\n".join(ans))


@alcommand(alc)
@assign("绑定")
@record("森空自动签到")
@exclusive
@accessable
async def reg(ctx: Context, token: Match[str], db: DatabaseService):
    sender = ctx.client.last_value
    if "content" in token.result:
        token.result = re.match('.*content(")?:(")?(?P<token>[^{}"]+).*', token.result)["token"]
    try:
        await bind(token.result)
    except RuntimeError as e:
        return await ctx.scene.send_message(str(e))
    async with db.get_session() as session:
        _record = SKAutoSignRecord(id=sender, token=token.result)
        await session.merge(_record)
        await session.commit()
    return await ctx.scene.send_message("森空岛自动签到录入成功")


@alcommand(alc)
@assign("解除")
@record("森空自动签到")
@exclusive
@accessable
async def rm(ctx: Context, db: DatabaseService):
    sender = ctx.client.last_value
    async with db.get_session() as session:
        _record = (await session.scalars(select(SKAutoSignRecord).where(SKAutoSignRecord.id == sender))).one_or_none()
        if not _record:
            return await ctx.scene.send_message("未绑定森空岛自动签到")
        for res in (
            await session.scalars(select(SKAutoSignResultRecord).where(SKAutoSignResultRecord.id == _record.id))
        ).all():
            await session.delete(res)
        await session.delete(_record)
        await session.commit()
        return await ctx.scene.send_message("解除森空岛自动签到成功")


@alcommand(alc)
@assign("查询")
@record("森空自动签到")
@exclusive
@accessable
async def check(ctx: Context, uid: Match[str], db: DatabaseService):
    sender = ctx.client.last_value
    async with db.get_session() as session:
        _record = (await session.scalars(select(SKAutoSignRecord).where(SKAutoSignRecord.id == sender))).one_or_none()
        if not _record:
            return await ctx.scene.send_message("未绑定森空岛自动签到")
        ans = []
        now = datetime.now()
        signed = now.replace(hour=0, minute=30, second=0, microsecond=0)
        if uid.available:
            for res in (
                await session.scalars(
                    select(SKAutoSignResultRecord)
                    .where(SKAutoSignResultRecord.id == _record.id)
                    .where(SKAutoSignResultRecord.uid == uid.result)
                    .where(SKAutoSignResultRecord.date >= signed)
                )
            ).all():
                ans.append(res.result["text"])
        else:
            for res in (
                await session.scalars(
                    select(SKAutoSignResultRecord)
                    .where(SKAutoSignResultRecord.id == _record.id)
                    .where(SKAutoSignResultRecord.date >= signed)
                )
            ).all():
                ans.append(res.result["text"])
        if not ans:
            return await ctx.scene.send_message("未进行签到，请等待")
        return await ctx.scene.send_message("\n".join(ans))


@crontab("30 0 * * * 0")
@record("森空自动签到", False)
async def shed():
    avilla = Avilla.current()
    results = {}
    async with bot.db.get_session() as session:
        for rec in (await session.scalars(select(SKAutoSignRecord))).all():
            ans = results.setdefault(rec.id, [])
            async for resp in sign(rec):  # type: ignore
                if resp["status"]:
                    res = SKAutoSignResultRecord(id=rec.id, uid=resp["target"], date=datetime.now(), result=resp)
                    await session.merge(res)
                    ans.append(resp["text"])
                await asyncio.sleep(1)
        await session.commit()
    for account in avilla.get_accounts(account_type=ElizabethAccount):
        async for friend in account.account.staff.query_entities("land.friend", friend=lambda x: x in results):
            ctx = account.account.get_context(friend)
            await ctx.scene.send_message("\n".join(results[friend["friend"]]))
