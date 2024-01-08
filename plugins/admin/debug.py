from __future__ import annotations

from arclet.alconna import Alconna, CommandMeta
from arclet.alconna.graia import alcommand
from avilla.core import Context
from avilla.standard.core.message import MessageReceived, MessageSent
from creart import it
from graia.saya import Saya
from graia.saya.builtins.broadcast.shortcut import listen, priority
from sqlalchemy import func, select

from app.config import BotConfig
from app.core import RaianBotService
from app.database import DatabaseService, Group, User
from app.shortcut import exclusive, permission


@listen(MessageReceived)
@priority(1)
def record_recv(bot: RaianBotService):
    recv = bot.cache.get("recv", 0)
    bot.cache["recv"] = recv + 1


@listen(MessageSent)
@priority(1)
def record_sent(bot: RaianBotService):
    sent = bot.cache.get("sent", 0)
    bot.cache["sent"] = sent + 1


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
async def debug(ctx: Context, db: DatabaseService, conf: BotConfig, bot: RaianBotService):
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
        f"自启动后共收到消息：  {bot.cache.get('recv', 0)} 条\n"
        f"自启动后共发出消息：  {bot.cache.get('sent', 0)} 条"
    )
    if disabled := bot.config.plugin.disabled:
        text += "\n已禁用模块:\n  - " + "\n  - ".join(disabled).replace(".", "::") + "\n"
    return await ctx.scene.send_message(text)
