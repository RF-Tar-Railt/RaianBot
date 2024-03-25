from secrets import token_hex

from arclet.alconna import Alconna, Args, CommandMeta, Field, Option
from arclet.alconna.graia import Match, alcommand, assign
from arknights_toolkit.gacha import ArknightsGacha, GachaUser
from avilla.core import Context, MessageChain, Picture, RawResource, Text
from avilla.core.exceptions import ActionFailed
from fastapi.responses import JSONResponse, Response
from graia.amnesia.builtins.aiohttp import AiohttpClientService
from graiax.fastapi import route
from sqlalchemy.sql import select

from app.core import RaianBotService
from app.database import DatabaseService, User
from app.shortcut import accessable, exclusive, picture, record

from .config import GachaConfig
from .model import ArkgachaRecord

bot = RaianBotService.current()
config = bot.config.plugin.get(GachaConfig)
gacha = ArknightsGacha(config.file or f"{bot.config.plugin_data_dir / 'gachapool.json'}", bot.config.proxy)


@route.route(["GET"], "/gacha/normal")
async def get_gacha(count: int = 10, per: int = 2, status: int = 0, img: bool = False):
    guser = GachaUser(per, status)
    if img:
        return Response(gacha.gacha_with_img(guser, count), media_type="image/png")
    data = gacha.gacha(guser, count)
    return JSONResponse([[i._asdict() for i in line] for line in data], headers={"charset": "utf-8"})


@route.route(["GET"], "/gacha/sim")
async def get_sim_gacha(per: int = 2, status: int = 0):
    from arknights_toolkit.gacha.simulate import simulate_image

    guser = GachaUser(per, status)
    data = gacha.gacha(guser, 10)
    return Response(await simulate_image(data[0]), media_type="image/png")


cmd = Alconna(
    "抽卡",
    Args[
        "count",
        int,
        Field(
            10, completion=lambda: "试试输入 300", unmatch_tips=lambda x: f"预期参数为数字，而不是 {x}\n例如：/抽卡 100"
        ),  # noqa: E501
    ],
    Option("更新", help_text="卡池更新"),
    meta=CommandMeta("模拟方舟寻访", example="$抽卡 300", extra={"supports": {"mirai", "qqapi"}}),
)


@alcommand(cmd, post=True, send_error=True)
@assign("更新")
@record("抽卡")
@exclusive
@accessable
async def change(ctx: Context, aio: AiohttpClientService):
    if new := (await gacha.update()):
        async with aio.session.get(new.pool) as resp:
            data = await resp.read()
        try:
            return await ctx.scene.send_message(
                MessageChain([Text(f"卡池已更新至: {new.title}"), Picture(RawResource(data))])
            )
        except Exception:
            await ctx.scene.send_message(MessageChain([Text(f"卡池已更新至: {new.title}")]))
            url = await bot.upload_to_cos(data, f"{new.title}.png")
            try:
                return await ctx.scene.send_message(picture(url, ctx))
            except ActionFailed:
                text = (
                    f"{new.title}\n六星角色：\n"
                    + "\n".join(f"{i.name} {'【限定】' if i.limit else '【常驻】'}" for i in new.six_chars)
                    + "\n五星角色：\n"
                    + "\n".join(f"{i.name} {'【限定】' if i.limit else '【常驻】'}" for i in new.five_chars)
                )
                return await ctx.scene.send_message(text)
    return await ctx.scene.send_message("卡池已经是最新状态！")


@alcommand(cmd, send_error=True, post=True)
@assign("$main")
@record("抽卡")
@exclusive
@accessable
async def gacha_(ctx: Context, count: Match[int], db: DatabaseService):
    """模拟抽卡"""
    count_ = min(max(count.result, 1), 300)
    async with db.get_session() as session:
        proba = (
            await session.scalars(select(ArkgachaRecord).where(ArkgachaRecord.id == ctx.client.user))
        ).one_or_none()

        if proba:
            guser = GachaUser(proba.per, proba.statis)
            result = gacha.gacha(guser, count_)
            data = gacha.create_image(guser, result, count_, True)
            proba.per = guser.six_per
            proba.statis = guser.six_statis
            await session.commit()
        else:
            user = (await session.scalars(select(User).where(User.id == ctx.client.user))).one_or_none()
            if user:
                guser = GachaUser(2, 0)
                result = gacha.gacha(guser, count_)
                data = gacha.create_image(guser, result, count_, True)
                proba = ArkgachaRecord(id=user.id, per=guser.six_per, statis=guser.six_statis)
                session.add(proba)
                await session.commit()
            else:
                guser = GachaUser()
                result = gacha.gacha(guser, count_)
                data = gacha.create_image(guser, result, count_, True)
                await ctx.scene.send_message("您未签到，抽卡水位是继承不了的说")
    try:
        return await ctx.scene.send_message(MessageChain([Picture(RawResource(data))]))
    except Exception:
        url = await bot.upload_to_cos(data, f"gacha_{token_hex(16)}.png")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            get_six = {}
            get_five = {}
            four_count = 0
            for ten in result:
                for res in ten:
                    if res.rarity == 6:
                        get_six[res.name] = get_six.get(res.name, 0) + 1
                    elif res.rarity == 5:
                        get_five[res.name] = get_five.get(res.name, 0) + 1
                    elif res.rarity == 4:
                        four_count += 1
            text = (
                f"抽卡次数: {count_}\n"
                f"六星角色：\n"
                + "\n".join(f"{i} x{get_six[i]}" for i in get_six)
                + "\n五星角色：\n"
                + "\n".join(f"{i} x{get_five[i]}" for i in get_five)
                + "\n四星角色：\n"
                + f"共{four_count}个四星"
            )
            return await ctx.scene.send_message(text)


@alcommand(
    Alconna(
        "十连",
        meta=CommandMeta(
            "生成仿真寻访图",
            usage="灰色头像表示新干员但是头图未更新",
            extra={"supports": {"mirai", "qqapi"}},
        ),
    ),
    send_error=True,
    post=True,  # noqa: E501
)
@record("抽卡")
@exclusive
@accessable
async def simulate(ctx: Context, db: DatabaseService):
    from arknights_toolkit.gacha.simulate import simulate_image

    async with db.get_session() as session:
        proba = (
            await session.scalars(select(ArkgachaRecord).where(ArkgachaRecord.id == ctx.client.user))
        ).one_or_none()

        if proba:
            guser = GachaUser(proba.per, proba.statis)
            result = gacha.gacha(guser, 10)
            data = await simulate_image(result[0])
            proba.per = guser.six_per
            proba.statis = guser.six_statis
            await session.commit()
        else:
            user = (await session.scalars(select(User).where(User.id == ctx.client.user))).one_or_none()
            if user:
                guser = GachaUser(2, 0)
                result = gacha.gacha(guser, 10)
                data = await simulate_image(result[0])
                proba = ArkgachaRecord(id=user.id, per=guser.six_per, statis=guser.six_statis)
                session.add(proba)
                await session.commit()
            else:
                guser = GachaUser()
                result = gacha.gacha(guser, 10)
                data = await simulate_image(result[0])
                await ctx.scene.send_message("您未签到，抽卡水位是继承不了的说")
    try:
        return await ctx.scene.send_message(MessageChain([Picture(RawResource(data))]))
    except Exception:
        url = await bot.upload_to_cos(data, f"gacha_sim_{token_hex(16)}.png")
        try:
            return await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed:
            get_six = {}
            get_five = {}
            four_count = 0
            for ten in result:
                for res in ten:
                    if res.rarity == 6:
                        get_six[res.name] = get_six.get(res.name, 0) + 1
                    elif res.rarity == 5:
                        get_five[res.name] = get_five.get(res.name, 0) + 1
                    elif res.rarity == 4:
                        four_count += 1
            text = (
                f"抽卡次数: {10}\n"
                f"六星角色：\n"
                + "\n".join(f"{i} x{get_six[i]}" for i in get_six)
                + "\n五星角色：\n"
                + "\n".join(f"{i} x{get_five[i]}" for i in get_five)
                + "\n四星角色：\n"
                + f"共{four_count}个四星"
            )
            return await ctx.scene.send_message(text)
