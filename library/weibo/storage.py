from abc import ABCMeta, abstractmethod
from pathlib import Path

import ujson

from .model import WeiboUser


class BaseWeiboData(metaclass=ABCMeta):
    followers: dict[str, WeiboUser]

    def __init__(self, filepath: str):
        self.path = Path(filepath)

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def save(self) -> None: ...


class DefaultWeiboData(BaseWeiboData):
    def load(self):
        if self.path.exists():
            with self.path.open("r+", encoding="UTF-8") as f_obj:
                _config = ujson.load(f_obj)
                if "weibo_follower" in _config:
                    _config = _config["weibo_follower"]
                self.followers = {k: WeiboUser.parse_obj(v) for k, v in _config.items()}
        else:
            self.followers = {}
            with self.path.open("w+", encoding="UTF-8") as f_obj:
                ujson.dump(self.followers, f_obj, ensure_ascii=False)

    def save(self):
        with self.path.open("w+", encoding="UTF-8") as f_obj:
            ujson.dump({k: v.dict() for k, v in self.followers.items()}, f_obj, ensure_ascii=False, indent=4)
