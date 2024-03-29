import asyncio
from datetime import datetime
from pathlib import Path

import ujson
from loguru import logger

from app.config import load_config
from app.database import Base, Group, User
from app.database.manager import DatabaseManager
from app.logger import setup_logger
from plugins.coc.model import CocRule
from plugins.draw.model import DrawRecord
from plugins.learn_repeat.model import Learn
from plugins.gacha.model import ArkgachaRecord
from plugins.sign.model import SignRecord
from plugins.sk_autosign.model import SKAutoSignRecord
from plugins.weibo.model import WeiboFollower

from sqlalchemy import select

config_dir_root = Path(input("输入当前配置根目录: >>>"))
if not config_dir_root.exists():
    logger.warning("未知的目录")
    exit(1)

cache_dir_root = Path(input("输入旧的缓存数据目录: >>>"))
if not cache_dir_root.exists():
    logger.warning("未知的目录")
    exit(1)

config = load_config(root_dir=str(config_dir_root))
setup_logger(config.log_level)
new_plugins = config.plugin_data_dir
new_plugins.mkdir(exist_ok=True, parents=True)

if config.database.type == "sqlite":
    config.database.name = f"{config.data_dir}/{config.database.name}"
    if not config.database.name.endswith(".db"):
        config.database.name = f"{config.database.name}.db"
db = DatabaseManager(config.database.url, {"echo": None, "pool_pre_ping": True})


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
                group = (await session.scalars(select(Group).where(Group.id == group_id))).one_or_none()
                if not group:
                    group = Group(
                        id=group_id,
                        platform="qq",
                        accounts=[f"land(qq).account({dr.name})"],
                        in_blacklist=data["in_blacklist"],
                        disabled=data["disabled"],
                    )
                    await session.merge(group)
                else:
                    group.accounts = [*group.accounts, f"land(qq).account({dr.name})"]
                    group.accounts = list(set(group.accounts))
                    group.disabled.extend(["member_mute", "member_unmute"])
                    group.disabled = list(set(group.disabled))
                    await session.merge(group)
                logger.info(f"migrating group {group_id} ...")
                if "weibo_followers" in data["additional"]:
                    for wid in data["additional"]["weibo_followers"][0]:
                        follower = WeiboFollower(id=group.id, wid=wid)
                        await session.merge(follower)
                if "coc_config" in data["additional"]:
                    rule = CocRule(id=group.id, rule=data["additional"]["coc_config"][0])
                    await session.merge(rule)
                await session.commit()

            for user_id, data in users.items():
                user = (await session.scalars(select(User).where(User.id == user_id))).one_or_none()
                if not user:
                    user = User(id=user_id, trust=data["trust"])
                    await session.merge(user)
                else:
                    user.trust = max(data["trust"], user.trust)
                    await session.merge(user)
                logger.info(f"migrating user {user_id} ...")
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

        plugins = cache_dir_root / "plugins"

        if (plugins / "skautosign.json").exists():
            with (plugins / "skautosign.json").open(encoding="utf-8") as f:
                table = ujson.load(f)
                for user_id, data in table.items():
                    if "origin" not in data:
                        continue
                    user = (await session.scalars(select(User).where(User.id == user_id))).one_or_none()
                    if not user:
                        user = User(id=user_id, trust=0)
                        await session.merge(user)
                    logger.info(f"migrating sk_auto_sign data of user {user_id} ...")
                    record = SKAutoSignRecord(id=user.id, token=data["origin"])
                    await session.merge(record)
                    await session.commit()

        if (plugins / "learn_repeat").exists():
            for dr in (plugins / "learn_repeat").iterdir():
                if dr.name == "image":
                    continue
                logger.info(f"migrating learn_repeat data of {dr.name} ...")
                for file in dr.iterdir():
                    group_id = file.stem[7:]
                    with file.open(encoding="utf-8") as f:
                        table = ujson.load(f)
                        for key, data in table.items():
                            author = f"group({group_id}).member({data['id']})"
                            content = ujson.loads(data["content"])
                            for elem in content:
                                if elem["type"] == "Image":
                                    path = Path(elem["path"])
                                    elem["path"] = str(new_plugins / "learn_repeat" / path.name)
                                elif elem["type"] == "Plain":
                                    elem["type"] = "Text"
                                elif elem["type"] == "Face":
                                    elem["id"] = str(elem.pop("face_id", 24))
                            record = Learn(gid=group_id, key=key, author=author, content=content)
                            await session.merge(record)
                            await session.commit()
            (new_plugins / "learn_repeat").mkdir(exist_ok=True, parents=True)
            for img in (plugins / "learn_repeat" / "image").iterdir():
                img.rename(new_plugins / "learn_repeat" / img.name)

        if (arkdb := (plugins / "arkrecord.db")).exists():
            arkdb.rename(new_plugins / "arkrecord.db")

        if (gachapool := (plugins / "gachapool.json")).exists():
            gachapool.rename(new_plugins / "gachapool.json")

        if (recordpool := (plugins / "recordpool.json")).exists():
            recordpool.rename(new_plugins / "recordpool.json")

        if (weibo := (plugins / "weibo_data.json")).exists():
            with weibo.open(encoding="utf-8") as f:
                table = ujson.load(f)
                with (new_plugins / "weibo_data.json").open("w+", encoding="utf-8") as nf:
                    ujson.dump(table["weibo_follower"], nf, ensure_ascii=False, indent=4)

    await db.stop()


asyncio.run(main())
logger.success(f"migrate completed")
