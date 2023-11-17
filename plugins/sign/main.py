import random
from datetime import datetime

from arclet.alconna import Alconna, CommandMeta
from arclet.alconna.graia import alcommand
from avilla.core import Context, Notice
from sqlalchemy.sql import select

from app.database import DatabaseService, User
from app.shortcut import accessable, record

from .config import SignConfig
from .model import SignRecord


@alcommand(Alconna("签到", meta=CommandMeta("在机器人处登记用户信息")), remove_tome=True, post=True)
@record("sign")
# @exclusive
@accessable
async def sign_up(ctx: Context, db: DatabaseService, config: SignConfig):
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
            return await ctx.scene.send_message(
                [Notice(ctx.client), "签到成功！\n当前信赖值：1\n初次签到提醒您：\n现在您可以抽卡与抽签了"],
            )
        sign = (await session.scalars(select(SignRecord).where(SignRecord.id == user.id))).one_or_none()
        if not sign:
            sign = SignRecord(id=user.id, date=today, count=1)
            user.trust += random.randint(1, 10) / 6.25
            session.add(sign)
            await session.commit()
            await session.refresh(user)
            return await ctx.scene.send_message(
                [Notice(ctx.client), "签到成功！\n当前信赖值：{user.trust:.3f}"],
            )
        if sign.date.day == today.day and sign.date.month == today.month:
            return await ctx.scene.send_message(
                [Notice(ctx.client), "您今天已与我签到!"],
            )
        sign.date = today
        sign.count += 1
        if user.trust < int(config.max):
            user.trust += random.randint(1, 10) / 6.25
            await session.commit()
            await session.refresh(user)
            return await ctx.scene.send_message(
                [Notice(ctx.client), f"签到成功！\n当前信赖值：{user.trust:.3f}"],
            )
        else:
            return await ctx.scene.send_message(
                [Notice(ctx.client), "签到成功！\n您的信赖已满！"],
            )
