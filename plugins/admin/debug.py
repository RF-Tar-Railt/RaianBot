from __future__ import annotations

from datetime import datetime, timedelta
from secrets import token_hex

from arclet.alconna import Alconna, Args, CommandMeta, Option
from arclet.alconna.graia import Match, alcommand, assign
from avilla.core import Context, LocalFileResource, Picture
from avilla.qqapi.exception import ActionFailed
from avilla.standard.core.message import MessageReceived
from creart import it
from graia.saya import Saya
from graia.saya.builtins.broadcast.shortcut import listen, priority
from sqlalchemy import func, select

from app.config import BotConfig
from app.core import RaianBotService
from app.database import DatabaseService, Group, User
from app.shortcut import exclusive, permission, picture
from app.statistic import draw_group_usage_statistics, draw_usage_statistics, draw_user_usage_statistics

bot = RaianBotService.current()
image_path = bot.config.plugin_data_dir / "statistic"
image_path.mkdir(exist_ok=True)


@listen(MessageReceived)
@priority(1)
def record_recv():
    recv = bot.cache.get("recv", 0)
    bot.cache["recv"] = recv + 1


@alcommand(
    Alconna(
        "调试",
        meta=CommandMeta(
            "显示调试信息",
            extra={"supports": {"mirai", "qqapi"}},
        ),
    ),
    post=True,
)
@permission("admin")
@exclusive
async def debug(ctx: Context, db: DatabaseService, conf: BotConfig):
    async with db.get_session() as session:
        all_group_count: int = (await session.execute(select(func.count("*")).select_from(Group))).first()[0]
        qqapi_group_count: int = (
            await session.execute(select(func.count("*")).select_from(Group).where(Group.platform == "qqapi"))
        ).first()[0]
        user_count: int = (await session.execute(select(func.count("*")).select_from(User))).first()[0]

    text = (
        f"{conf.name} ({conf.account}) 调试信息\n"
        f"当前共加载模块：     {len(it(Saya).channels)} 个\n"
        f"当前共加入群与频道：  {all_group_count} 个\n"
        f"官方接口下的频道与群：{qqapi_group_count} 个\n"
        f"参与机器人交互的用户：{user_count} 人\n"
        f"自启动后共收到消息：  {bot.cache.get('recv', 0)} 条"
    )
    if disabled := bot.config.plugin.disabled:
        text += "\n已禁用模块:\n  - " + "\n  - ".join(disabled).replace(".", "::") + "\n"
    return await ctx.scene.send_message(text)


stat = Alconna(
    "统计",
    Args["time", ["天", "周", "月", "年", "总"], "天"],
    Option("群组", Args["group?", str]),
    Option("用户", Args["user?", str]),
    meta=CommandMeta(
        "显示统计信息",
        extra={"supports": {"mirai", "qqapi"}},
    ),
)


def handle_time(time: str):
    now = datetime.now()
    if time == "天":
        return now - timedelta(days=1), now
    elif time == "周":
        return now - timedelta(days=7), now
    elif time == "月":
        return now - timedelta(days=30), now
    elif time == "年":
        return now - timedelta(days=365), now
    elif time == "总":
        return datetime.fromtimestamp(0), now


@alcommand(stat, post=True, send_error=True)
@assign("$main")
@permission("admin")
@exclusive
async def statistic(ctx: Context, db: DatabaseService, time: Match[str]):
    start_time, end_time = handle_time(time.result)
    file = image_path / f"statistic_{time.result}.png"
    await draw_usage_statistics(db, start_time, end_time, str(file.absolute()))
    try:
        return await ctx.scene.send_message(Picture(LocalFileResource(file)))
    except Exception:
        url = await bot.upload_to_cos(file.read_bytes(), f"statistic_{token_hex(16)}.jpg")
        try:
            await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed as e:
            return await ctx.scene.send_message(f"图片发送失败: {e}")


@alcommand(stat, post=True, send_error=True)
@assign("群组")
@permission("admin")
@exclusive
async def group_statistic(ctx: Context, db: DatabaseService, time: Match[str], group: Match[str]):
    start_time, end_time = handle_time(time.result)
    file = image_path / f"group_statistic_{time.result}.png"
    await draw_group_usage_statistics(db, group.result, start_time, end_time, str(file.absolute()))
    try:
        return await ctx.scene.send_message(Picture(LocalFileResource(file)))
    except Exception:
        url = await bot.upload_to_cos(file.read_bytes(), f"group_statistic_{token_hex(16)}.jpg")
        try:
            await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed as e:
            return await ctx.scene.send_message(f"图片发送失败: {e}")


@alcommand(stat, post=True, send_error=True)
@assign("用户")
@permission("admin")
@exclusive
async def user_statistic(ctx: Context, db: DatabaseService, time: Match[str], user: Match[str]):
    start_time, end_time = handle_time(time.result)
    file = image_path / f"user_statistic_{time.result}.png"
    await draw_user_usage_statistics(db, user.result, start_time, end_time, str(file.absolute()))
    try:
        return await ctx.scene.send_message(Picture(LocalFileResource(file)))
    except Exception:
        url = await bot.upload_to_cos(file.read_bytes(), f"user_statistic_{token_hex(16)}.jpg")
        try:
            await ctx.scene.send_message(picture(url, ctx))
        except ActionFailed as e:
            return await ctx.scene.send_message(f"图片发送失败: {e}")
