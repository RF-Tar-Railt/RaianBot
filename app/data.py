from __future__ import annotations

from pathlib import Path
from typing import (
    Callable,
    Dict,
    List,
    NamedTuple,
    Sequence,
    Type,
    TypeVar,
    cast,
    get_origin,
    overload,
)
import ujson
from pydantic import BaseModel, Field
from pydantic.class_validators import validator

from .logger import logger
from .context import DataInstance, MainConfigInstance
from .config import BotConfig

TMeta = TypeVar("TMeta", bound=tuple)
TModel = TypeVar("TModel", bound=BaseModel)
DATA_VERSION = 3


class BaseProfile(BaseModel):
    additional: Dict[str, Sequence] = Field(default_factory=dict)

    @overload
    def get(self, __t: type[TMeta]) -> TMeta | None:
        ...

    @overload
    def get(self, __t: type[TMeta], __d: TMeta) -> TMeta:
        ...

    def get(self, __t: type[TMeta], __d: TMeta | None = None):
        if data := self.additional.get(__t.__name__):
            if not isinstance(data, __t):
                data = __t(*data)
                self.additional[__t.__name__] = data
            return data
        return __d

    def set(self, __v: TMeta):
        self.additional[type(__v).__name__] = __v

    @validator("additional", allow_reuse=True, pre=True)
    def validate_event_type(cls, v: dict):
        """验证事件类型, 通过比对 type 字段实现"""
        for k, s in v.copy().items():
            if not isinstance(s, Sequence):
                v[k] = [s]
        return v


class GroupProfile(BaseProfile):
    id: int
    disabled: List[str] = Field(default_factory=list)
    in_blacklist: bool = Field(default=False)


class UserProfile(BaseProfile):
    id: int
    trust: float = Field(default=0)

    class Config:
        extra = "ignore"


class BotDataManager:
    disable_functions: set[str]
    __functions: dict[str, Callable]
    __group_profiles: dict[str, GroupProfile]
    __user_profiles: dict[str, UserProfile]
    __cache_data: dict
    __metas: dict[str, dict[str, type[tuple]]]

    @staticmethod
    def validate_meta(schema: type[TMeta], data: Sequence):
        if isinstance(data, schema):
            return True
        meta = cast(Type[NamedTuple], schema)
        if len(meta.__annotations__) != len(data):
            return False
        return all(isinstance(di, get_origin(si) or si) for si, di in zip(meta.__annotations__.values(), data))

    def __init__(self, config: BotConfig):
        base = MainConfigInstance.get(None)
        base_dir_path = Path(base.cache_dir)
        base_dir_path.mkdir(exist_ok=True, parents=True)
        self.__loaded = False
        self.__functions = {}
        self.__metas = {"group_meta": {}, "user_meta": {}}
        self.disable_functions = set()
        self.group_path = base_dir_path / str(config.account) / "groups_data.json"
        self.user_path = base_dir_path / str(config.account) / "users_data.json"
        self.cache_path = base_dir_path / str(config.account) / "basic_data.json"
        # self.plugins_path = base_dir_path / str(config.account) / base.plugin.root
        # self.plugins_path.mkdir(exist_ok=True, parents=True)
        self.__group_profiles = {}
        self.__user_profiles = {}
        self.__cache_data = {"all_joined_group": [], "blacklist": []}

        if data := DataInstance.get(None):
            data[config.account] = self
        else:
            DataInstance.set({config.account: self})

    def add_meta(self, **kwargs: list[type[TMeta]]):
        for k, v in kwargs.items():
            metas = self.__metas.setdefault(k, {})
            for s in v:
                metas[s.__name__] = s

    def add_group(self, gid: int, **kwargs):
        for k, v in kwargs.items():
            if k not in self.__metas["group_meta"]:
                raise ValueError(k)
            if not self.validate_meta(self.__metas["group_meta"][k], v):
                raise TypeError(v)
        self.__group_profiles[str(gid)] = GroupProfile(
            id=gid,
            additional=kwargs,
            in_blacklist=(gid in self.__cache_data.get("blacklist", {})),
            disabled=list(self.disable_functions),
        )
        return self.__group_profiles[str(gid)]

    def add_user(self, uid: int, **kwargs):
        for k, v in kwargs.items():
            if k not in self.__metas["user_meta"]:
                raise ValueError(k)
            if not self.validate_meta(self.__metas["user_meta"][k], v):
                raise TypeError(v)
        self.__user_profiles[str(uid)] = UserProfile(id=uid, additional=kwargs)
        return self.__user_profiles[str(uid)]

    def exist(self, id_: int):
        return (str(id_) in self.__user_profiles) or (str(id_) in self.__group_profiles)

    def get_group(self, gid: int) -> GroupProfile:
        if tg := self.__group_profiles.get(str(gid), None):
            for k, v in tg.additional.copy().items():
                if (schema := self.__metas["group_meta"].get(k)) and not isinstance(v, schema):
                    tg.additional[k] = schema(*v)
            return tg
        raise ValueError(gid)

    def get_user(self, uid: int) -> UserProfile:
        if tu := self.__user_profiles.get(str(uid), None):
            for k, v in tu.additional.copy().items():
                if (schema := self.__metas["user_meta"].get(k)) and not isinstance(v, schema):
                    tu.additional[k] = schema(*v)
            return tu
        raise ValueError(uid)

    def remove_user(self, id_: int):
        return self.__user_profiles.pop(str(id_))

    def remove_group(self, id_: int):
        return self.__group_profiles.pop(str(id_))

    def update_group(self, group: GroupProfile):
        for k, v in group.additional.items():
            if k not in self.__metas["group_meta"]:
                raise ValueError(k)
            if not self.validate_meta(self.__metas["group_meta"][k], v):
                raise TypeError(v)
        self.__group_profiles[str(group.id)] = group

    def update_user(self, user: UserProfile):
        for k, v in user.additional.items():
            if k not in self.__metas["user_meta"]:
                raise ValueError(k)
            if not self.validate_meta(self.__metas["user_meta"][k], v):
                raise TypeError(v)
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

    @property
    def funcs(self):
        return list(self.__functions.keys())

    def load(self):
        if self.group_path.exists():
            with self.group_path.open("r+", encoding="UTF-8") as f_obj:
                self.__group_profiles = self._check_load(f_obj, "群组数据已过期！请先运行 'data_migrator.py' !", GroupProfile)

        else:
            with self.group_path.open("w+", encoding="UTF-8") as f_obj:
                ujson.dump({"version": DATA_VERSION, "data": {}}, f_obj, ensure_ascii=False)

        if self.user_path.exists():
            with self.user_path.open("r+", encoding="UTF-8") as f_obj:
                self.__user_profiles = self._check_load(f_obj, "用户数据已过期！请先运行 'data_migrator.py' !", UserProfile)

        else:
            with self.user_path.open("w+", encoding="UTF-8") as f_obj:
                ujson.dump({"version": DATA_VERSION, "data": {}}, f_obj, ensure_ascii=False)

        if self.cache_path.exists():
            with self.cache_path.open("r+", encoding="UTF-8") as f_obj:
                self.__cache_data = ujson.load(f_obj)
        else:
            with self.user_path.open("w+", encoding="UTF-8") as f_obj:
                ujson.dump(self.__cache_data, f_obj, ensure_ascii=False)
        self.__loaded = True

    @staticmethod
    def _check_load(file, error, model: Type[TModel]) -> dict[str, TModel]:
        _info: dict = ujson.load(file)
        if _info.get("version", 1) < DATA_VERSION:
            logger.critical(error)
            file.close()
            raise RuntimeError
        return {k: model.parse_obj(v) for k, v in _info["data"].items()}

    def save(self):
        if not self.__loaded:
            return
        with self.user_path.open("w+", encoding="UTF-8") as fo:
            ujson.dump(
                {"version": DATA_VERSION, "data": {k: v.dict() for k, v in self.__user_profiles.items()}},
                fo,
                ensure_ascii=False,
                indent=2,
            )
        with self.group_path.open("w+", encoding="UTF-8") as fo:
            ujson.dump(
                {"version": DATA_VERSION, "data": {k: v.dict() for k, v in self.__group_profiles.items()}},
                fo,
                ensure_ascii=False,
                indent=2,
            )
        with self.cache_path.open("w+", encoding="UTF-8") as fo:
            ujson.dump(self.__cache_data, fo, ensure_ascii=False, indent=2)

    def record(self, name: str, disable: bool = False):
        def __wrapper__(func):
            self.__functions.setdefault(name, func)
            func.__record__ = name
            if disable:
                self.disable_functions.add(name)
            return func

        return __wrapper__

    def func_description(self, name: str):
        return func.__doc__ if (func := self.__functions.get(name)) else "Unknown"

    def clear(self):
        self.__user_profiles.clear()
        self.__group_profiles.clear()
        self.__cache_data.clear()
        self.disable_functions.clear()
        self.__functions.clear()
        self.__metas.clear()



__all__ = ["BotDataManager", "GroupProfile", "UserProfile"]
