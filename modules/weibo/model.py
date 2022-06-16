from typing import TypedDict, Literal
from pydantic import BaseModel, Field


class WeiboTableCount(TypedDict):
    profile: int
    weibo: int
    video: int
    album: int


class WeiboUser(BaseModel):
    id: str
    name: str
    avatar: str
    statues: int
    counts: WeiboTableCount = Field(default_factory=lambda: {"profile": 0, "weibo": 0, "video": 0, "album": 0})

    __mapping = {
        "profile": 230283,
        "weibo": 107603,
        "video": 231567,
        "album": 107803
    }

    def contain_id(self, keys: Literal["profile", "weibo", "video", "album"]) -> str:
        return f"{self.__mapping[keys]}{self.id}"
