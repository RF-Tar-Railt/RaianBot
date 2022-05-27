import ujson
from pathlib import Path
from typing import Dict
from weakref import finalize
from arclet.alconna.util import Singleton

from .config import BotConfig
from .model import UserProfile, GroupProfile


class BotDataManager(metaclass=Singleton):
    __group_profiles: Dict[str, GroupProfile]
    __user_profiles: Dict[str, UserProfile]
    __cache_data: dict

    def __init__(self, config: BotConfig):
        self.config = config

        dir_path = Path(config.cache_dir)
        dir_path.mkdir(exist_ok=True)
        self.group_path = dir_path / "groups_data.json"
        self.user_path = dir_path / "users_data.json"
        self.cache_path = dir_path / "basic_data.json"

        if self.group_path.exists():
            with self.group_path.open('r+', encoding='UTF-8') as f_obj:
                _info = ujson.load(f_obj)
                self.__group_profiles = {k: GroupProfile.parse_obj(v) for k, v in _info.items()}
        else:
            self.__group_profiles = {}
            with self.group_path.open('w+', encoding='UTF-8') as f_obj:
                ujson.dump({}, f_obj, ensure_ascii=False)

        if self.user_path.exists():
            with self.user_path.open('r+', encoding='UTF-8') as f_obj:
                _info = ujson.load(f_obj)
                self.__user_profiles = {k: UserProfile.parse_obj(v) for k, v in _info.items()}
        else:
            self.__user_profiles = {}
            with self.user_path.open('w+', encoding='UTF-8') as f_obj:
                ujson.dump({}, f_obj, ensure_ascii=False)

        if self.cache_path.exists():
            with self.cache_path.open('r+', encoding='UTF-8') as f_obj:
                self.__cache_data = ujson.load(f_obj)
        else:
            self.__cache_data = {"all_joined_group": [], "blacklist": []}
            with self.user_path.open('w+', encoding='UTF-8') as f_obj:
                ujson.dump(self.__cache_data, f_obj, ensure_ascii=False)

        def _s(mgr: "BotDataManager"):
            mgr.save()
            mgr.__user_profiles.clear()
            mgr.__group_profiles.clear()
            mgr.__cache_data.clear()
            Singleton.remove(self.__class__)

        finalize(self, _s, self)

    def add_group(self, gid: int, **kwargs):
        for k, v in kwargs.items():
            if k not in self.config.group_meta:
                raise ValueError
        self.__group_profiles[str(gid)] = GroupProfile(
            id=gid, additional=kwargs, in_blacklist=(gid in self.__cache_data['blacklist'])
        )

    def add_user(self, uid: int, **kwargs):
        for k, v in kwargs.items():
            if k not in self.config.user_meta:
                raise ValueError
        self.__user_profiles[str(uid)] = UserProfile(id=uid, additional=kwargs)

    def exist(self, id_: int):
        return (str(id_) in self.__user_profiles) or (str(id_) in self.__group_profiles)

    def get_group(self, gid: int):
        return self.__group_profiles.get(str(gid), None)

    def get_user(self, uid: int):
        return self.__user_profiles.get(str(uid), None)

    def remove_user(self, id_: int):
        return self.__user_profiles.pop(str(id_))

    def remove_group(self, id_: int):
        return self.__group_profiles.pop(str(id_))

    def update_group(
            self,
            group: GroupProfile
    ):
        for k, v in group.additional.items():
            if k not in self.config.group_meta:
                raise ValueError
        self.__group_profiles[str(group.id)] = group

    def update_user(
            self,
            user: UserProfile
    ):
        for k, v in user.additional.items():
            if k not in self.config.user_meta:
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
        with self.user_path.open('w+', encoding='UTF-8') as fo:
            ujson.dump(
                {k: v.dict() for k, v in self.__user_profiles.items()},
                fo, ensure_ascii=False, indent=2
            )
        with self.group_path.open('w+', encoding='UTF-8') as fo:
            ujson.dump(
                {k: v.dict() for k, v in self.__group_profiles.items()},
                fo, ensure_ascii=False, indent=2
            )
        with self.cache_path.open('w+', encoding='UTF-8') as fo:
            ujson.dump(self.__cache_data, fo, ensure_ascii=False, indent=2)


__all__ = ["BotDataManager"]
