import asyncio
from datetime import datetime
from pathlib import Path

import ujson
from loguru import logger

from app.config import SqliteDatabaseConfig, load_config
from app.database import Base, Group, User, get_engine_url
from app.database.manager import DatabaseManager
from app.logger import setup_logger
from plugins.coc.model import CocRule
from plugins.draw.model import DrawRecord
from plugins.gacha.model import ArkgachaRecord
from plugins.sign.model import SignRecord
from plugins.weibo.model import WeiboFollower

config_dir_root = Path(input("输入当前配置根目录: >>>"))
if not config_dir_root.exists():
    logger.warning("未知的目录")
    exit(1)

cache_dir_root = Path(input("输入当前缓存数据目录: >>>"))
if not cache_dir_root.exists():
    logger.warning("未知的目录")
    exit(1)

config = load_config(root_dir=str(config_dir_root))
setup_logger(config.log_level)


if isinstance(config.database, SqliteDatabaseConfig):
    config.database.name = f"/{config.data_dir}/{config.database.name}"
    if not config.database.name.endswith(".db"):
        config.database.name = f"{config.database.name}.db"
db = DatabaseManager(get_engine_url(**config.database.dict()), {"echo": None, "pool_pre_ping": True})


async def main():
    logger.info("Initializing database...")
    await db.initialize()
    get_session = db.session_factory
    logger.success("Database initialized!")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.success("Database tables created!")
    async with get_session() as session:
        for dr in cache_dir_root.iterdir():
            if not (dr.name.isdigit() and dr.is_dir()):
                continue

            logger.info(f"migrating data of {dr.name} ...")
            with (dr / "groups_data.json").open(encoding="utf-8") as f:
                groups = ujson.load(f)["data"]

            with (dr / "users_data.json").open(encoding="utf-8") as f:
                users = ujson.load(f)["data"]

            for group_id, data in groups.items():
                group = Group(
                    id=group_id,
                    platform="qq",
                    accounts=[f"land(qq).account({dr.name})"],
                    in_blacklist=data["in_blacklist"],
                    disabled=data["disabled"],
                )
                await session.merge(group)
                logger.debug(f"migrating group {group_id} ...")
                if "weibo_followers" in data["additional"]:
                    for wid in data["additional"]["weibo_followers"][0]:
                        follower = WeiboFollower(id=group.id, wid=wid)
                        await session.merge(follower)
                if "coc_config" in data["additional"]:
                    rule = CocRule(id=group.id, rule=data["additional"]["coc_config"][0])
                    await session.merge(rule)
                await session.commit()

            for user_id, data in users.items():
                user = User(id=user_id, trust=data["trust"])
                await session.merge(user)
                logger.debug(f"migrating user {user_id} ...")
                now = datetime.now()
                now = now.replace(day=now.day - 1, month=10)
                sign_record = SignRecord(id=user.id, date=now, count=int(user.trust // 1.2))
                if "sign_info" in data["additional"]:
                    month, day = data["additional"]["sign_info"]
                    sign_record.date.replace(month=month, day=day)
                await session.merge(sign_record)

                if "draw_info" in data["additional"]:
                    day, ans = data["additional"]["draw_info"]
                    if day != -1:
                        draw = DrawRecord(id=user.id, date=now.replace(day=day), answer=ans)
                        await session.merge(draw)

                if "arkgacha_proba" in data["additional"]:
                    statis, per = data["additional"]["arkgacha_proba"]
                    gacha = ArkgachaRecord(id=user.id, statis=statis, per=per)
                    await session.merge(gacha)
                await session.commit()

    await db.stop()


asyncio.run(main())
logger.success(f"migrate completed")
