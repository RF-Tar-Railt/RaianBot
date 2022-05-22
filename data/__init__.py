import json
from pathlib import Path
from typing import Dict
from weakref import finalize
from arclet.alconna.util import Singleton

from config import bot_config
from .model import UserProfile, GroupProfile

group_path = Path(__file__).parent / "groups_data.json"
user_path = Path(__file__).parent / "users_data.json"
cache_path = Path(__file__).parent / "cache_data.json"


class BotDataManager(metaclass=Singleton):
    __group_profiles: Dict[str, GroupProfile]
    __user_profiles: Dict[str, UserProfile]
    __cache_data: dict

    def __init__(self):
        if group_path.exists():
            with group_path.open('r+', encoding='UTF-8') as f_obj:
                _info = json.load(f_obj)
                self.__group_profiles = {k: GroupProfile.parse_obj(v) for k, v in _info.items()}
        else:
            self.__group_profiles = {}
            with group_path.open('w+', encoding='UTF-8') as f_obj:
                json.dump({}, f_obj, ensure_ascii=False)

        if user_path.exists():
            with user_path.open('r+', encoding='UTF-8') as f_obj:
                _info = json.load(f_obj)
                self.__user_profiles = {k: UserProfile.parse_obj(v) for k, v in _info.items()}
        else:
            self.__user_profiles = {}
            with user_path.open('w+', encoding='UTF-8') as f_obj:
                json.dump({}, f_obj, ensure_ascii=False)

        if cache_path.exists():
            with cache_path.open('r+', encoding='UTF-8') as f_obj:
                self.__cache_data = json.load(f_obj)
        else:
            self.__cache_data = {}
            with user_path.open('w+', encoding='UTF-8') as f_obj:
                json.dump({}, f_obj, ensure_ascii=False)

        def _s(mgr: "BotDataManager"):
            mgr.save()
            mgr.__user_profiles.clear()
            mgr.__group_profiles.clear()
            mgr.__cache_data.clear()
            Singleton.remove(self.__class__)

        finalize(self, _s, self)

    def add_group(self, gid: int, **kwargs):
        for k, v in kwargs.items():
            if k not in bot_config.group_meta:
                raise ValueError
        self.__group_profiles[str(gid)] = GroupProfile(id=gid, additional=kwargs)

    def add_user(self, uid: int, **kwargs):
        for k, v in kwargs.items():
            if k not in bot_config.user_meta:
                raise ValueError
        self.__user_profiles[str(uid)] = UserProfile(id=uid, additional=kwargs)

    def exist(self, id_: int):
        return (str(id_) in self.__user_profiles) or (str(id_) in self.__group_profiles)

    def get_group(self, gid: int):
        return self.__group_profiles.get(str(gid), None)

    def get_user(self, uid: int):
        return self.__user_profiles.get(str(uid), None)

    def update_group(
            self,
            group: GroupProfile
    ):
        for k, v in group.additional.items():
            if k not in bot_config.group_meta:
                raise ValueError
        self.__group_profiles[str(group.id)] = group

    def update_user(
            self,
            user: UserProfile
    ):
        for k, v in user.additional.items():
            if k not in bot_config.user_meta:
                raise ValueError
        self.__user_profiles[str(user.id)] = user

    @property
    def users(self):
        return list(self.__user_profiles.keys())

    @property
    def groups(self):
        return list(self.__group_profiles.keys())

    @property
    def cache(self):
        return self.__cache_data

    def save(self):
        with user_path.open('w+', encoding='UTF-8') as fo:
            json.dump(
                {k: v.dict() for k, v in self.__user_profiles.items()},
                fo, ensure_ascii=False, indent=2
            )
        with group_path.open('w+', encoding='UTF-8') as fo:
            json.dump(
                {k: v.dict() for k, v in self.__group_profiles.items()},
                fo, ensure_ascii=False, indent=2
            )
        with cache_path.open('w+', encoding='UTF-8') as fo:
            json.dump(self.__cache_data, fo, ensure_ascii=False, indent=2)


bot_data = BotDataManager()

__all__ = ["bot_data"]
