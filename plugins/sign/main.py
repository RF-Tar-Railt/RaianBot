import random
from datetime import datetime

from arclet.alconna import Alconna, CommandMeta
from arclet.alconna.graia import alcommand
from avilla.core import Context, Message
from sqlalchemy.sql import select

from app.database import DatabaseService, User
from app.shortcut import accessable, is_qqapi_group, record

from .config import SignConfig
from .model import SignRecord


@alcommand(Alconna("签到", meta=CommandMeta("在机器人处登记用户信息")), post=True, send_error=True)
@record("sign")
# @exclusive
@accessable
async def sign_up(ctx: Context, msg: Message, db: DatabaseService, config: SignConfig):
    """在机器人处登记信息"""
    today = datetime.now()
    async with db.get_session() as session:
        user = (await session.scalars(select(User).where(User.id == ctx.client.last_value))).one_or_none()
        if not user:
            user = User(id=ctx.client.last_value, trust=1)
            session.add(user)
            sign = SignRecord(id=user.id, date=today, count=1)
            session.add(sign)
            await session.commit()
            await session.refresh(user)
            if is_qqapi_group(ctx):
                return await ctx.scene.send_message(
                    "签到成功！\n" "当前信赖值：1\n" "初次签到提醒您：\n" "现在您可以抽卡与抽签了",
                )
            return await ctx.scene.send_message(
                "签到成功！\n" "当前信赖值：1\n" "初次签到提醒您：\n" "现在您可以抽卡与抽签了",
                reply=msg,
            )
        sign = (await session.scalars(select(SignRecord).where(SignRecord.id == user.id))).one_or_none()
        if not sign:
            sign = SignRecord(id=user.id, date=today, count=1)
            user.trust += random.randint(1, 10) / 6.25
            session.add(sign)
            await session.commit()
            await session.refresh(user)
            if is_qqapi_group(ctx):
                return await ctx.scene.send_message(f"签到成功！\n当前信赖值：{user.trust:.3f}")
            return await ctx.scene.send_message(f"签到成功！\n当前信赖值：{user.trust:.3f}", reply=msg)
        if sign.date.day == today.day and sign.date.month == today.month:
            if is_qqapi_group(ctx):
                return await ctx.scene.send_message("您今天已与我签到!")
            return await ctx.scene.send_message("您今天已与我签到!", reply=msg)
        sign.date = today
        sign.count += 1
        if user.trust < int(config.max):
            user.trust += random.randint(1, 10) / 6.25
            await session.commit()
            await session.refresh(user)
            if is_qqapi_group(ctx):
                return await ctx.scene.send_message(f"签到成功！\n当前信赖值：{user.trust:.3f}")
            return await ctx.scene.send_message(f"签到成功！\n当前信赖值：{user.trust:.3f}", reply=msg)
        else:
            if is_qqapi_group(ctx):
                return await ctx.scene.send_message("签到成功！\n您的信赖已满！")
            return await ctx.scene.send_message("签到成功！\n您的信赖已满！", reply=msg)
