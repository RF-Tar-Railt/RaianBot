import json
import random
from datetime import datetime

from arclet.alconna import Alconna, CommandMeta
from arclet.alconna.graia import alcommand
from avilla.core import Context, Message
from sqlalchemy import select

from app.database import DatabaseService, User
from app.shortcut import accessable, is_qqapi_group, record
from library.rand import random_pick_small

from .model import DrawRecord

with open("assets/data/draw_poetry.json", encoding="UTF-8") as f_obj:
    draw_poetry: list = json.load(f_obj)


def get_draw():
    some_list = [0, 1, 2, 3, 4, 5, 6]  # 大凶，凶，末吉，小吉，中吉，吉，大吉
    probabilities = [0.09, 0.25, 0.06, 0.07, 0.11, 0.25, 0.17]
    draw_num = random_pick_small(some_list, probabilities)
    poetry_data = draw_poetry[draw_num]
    draw_ans = poetry_data["type"]
    text = poetry_data["poetry"][random.randint(1, poetry_data["count"]) - 1]
    return draw_ans, text


@alcommand(Alconna("抽签", meta=CommandMeta("进行一次抽签, 可以解除")), post=True, send_error=True)
@record("抽签")
# @exclusive
@accessable
async def draw(ctx: Context, msg: Message, db: DatabaseService):
    """每日运势抽签"""
    today = datetime.now()
    async with db.get_session() as session:
        draw_record = (
            await session.scalars(select(DrawRecord).where(DrawRecord.id == ctx.client.last_value))
        ).one_or_none()
        if draw_record:
            if draw_record.date.day == today.day and draw_record.date.month == today.month:
                if is_qqapi_group(ctx):
                    return await ctx.scene.send_message(f"您今天已经抽过签了哦，运势为{draw_record.answer}")
                return await ctx.scene.send_message(f"您今天已经抽过签了哦，运势为{draw_record.answer}", reply=msg)
            answer, poetry = get_draw()
            draw_record.date = today
            draw_record.answer = answer
            await session.commit()
            await session.refresh(draw_record)
        else:
            user = (await session.scalars(select(User).where(User.id == ctx.client.last_value))).one_or_none()
            if not user:
                if is_qqapi_group(ctx):
                    return await ctx.scene.send_message("您还未找我签到~")
                return await ctx.scene.send_message("您还未找我签到~", reply=msg)
            answer, poetry = get_draw()
            draw_record = DrawRecord(id=user.id, date=today, answer=answer)
            session.add(draw_record)
            await session.commit()
        if is_qqapi_group(ctx):
            return await ctx.scene.send_message(f"您今日的运势抽签为：{answer}\n{poetry}")
        return await ctx.scene.send_message(f"您今日的运势抽签为：{answer}\n{poetry}", reply=msg)


@alcommand(Alconna("解签", meta=CommandMeta("解除上一次的抽签")), post=True, send_error=True)
@record("抽签")
# @exclusive
@accessable
async def undraw(ctx: Context, msg: Message, db: DatabaseService):
    async with db.get_session() as session:
        user = (await session.scalars(select(User).where(User.id == ctx.client.last_value))).one_or_none()
        if not user:
            if is_qqapi_group(ctx):
                return await ctx.scene.send_message("您还未找我签到~")
            return await ctx.scene.send_message("您还未找我签到~", reply=msg)
        draw_record = (await session.scalars(select(DrawRecord).where(DrawRecord.id == user.id))).one_or_none()
        if not draw_record:
            if is_qqapi_group(ctx):
                return await ctx.scene.send_message("您今日还未抽签~")
            return await ctx.scene.send_message("您今日还未抽签~", reply=msg)
        await session.delete(draw_record)
        await session.commit()
        if is_qqapi_group(ctx):
            return await ctx.scene.send_message("您已成功解签")
        return await ctx.scene.send_message("您已成功解签", reply=msg)
