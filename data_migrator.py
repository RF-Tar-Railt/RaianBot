from pathlib import Path
import ujson
from loguru import logger

cache_dir_root = Path(input("输入当前缓存数据目录: >>>"))
if not cache_dir_root.exists():
    logger.warning("未知的目录")
    exit(1)

if (gd := cache_dir_root / "groups_data.json").exists():
    logger.info("处理群组数据中。。。")
    with gd.open("r+", encoding='utf-8') as f:
        data: dict = ujson.load(f)
    if data.get('version', 1) < 2:
        for gid in data.keys():
            logger.debug(f"当前处理群组: {gid}")
            group: dict = data[gid]
            if add := group.get("additional", {}):
                add: dict
                if 'mute' in add:
                    add['mute'] = [add['mute']]
                if 'weibo_followers' in add:
                    add['weibo_followers'] = [add['weibo_followers']]
                if 'roles' in add:
                    add['roles'] = [add['roles']]
            logger.debug(f"处理群组 {gid} 完成")
        with gd.open("w", encoding='utf-8') as f:
            ujson.dump({"version": 2, "data": data}, f, ensure_ascii=False, indent=2)
    logger.success("处理群组数据完成")

if (ud := cache_dir_root / "users_data.json").exists():
    logger.info("处理用户数据中。。。")
    with ud.open("r+", encoding='utf-8') as f:
        data: dict = ujson.load(f)
    if data.get('version', 1) < 2:
        for uid in data.keys():
            logger.debug(f"当前处理用户: {uid}")
            user: dict = data[uid]
            if add := user.get("additional", {}):
                add: dict
                if 'gacha_proba' in add:
                    add['arkgacha_proba'] = add['gacha_proba']['arknights']
                    del add['gacha_proba']
            logger.debug(f"处理用户 {uid} 完成")
        with ud.open("w", encoding='utf-8') as f:
            ujson.dump({"version": 2, "data": data}, f, ensure_ascii=False, indent=2)
    logger.success("处理用户数据完成")