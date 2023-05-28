from typing import Literal, Optional, List
from pydantic import BaseModel, Field


class WeiboUser(BaseModel):
    id: int
    name: str
    description: str = Field(default='')
    avatar: str = Field(default='')
    statuses: int = Field(default=0)
    visitable: bool = Field(default=True)
    total: int = Field(default=0)
    latest: str = Field(default='')

    __mapping = {
        "info": 100505,
        "profile": 230283,
        "weibo": 107603,
        "video": 231567,
        "album": 107803
    }

    @property
    def info_link(self):
        return f"https://m.weibo.cn/u/{self.id}"

    @property
    def info_data(self):
        return f"https://m.weibo.cn/api/container/getIndex?{self.contain_id('info')}"

    def contain_id(self, keys: Literal["info", "profile", "weibo", "video", "album"]) -> str:
        return f"{self.__mapping[keys]}{self.id}"


class WeiboDynamic(BaseModel):
    bid: str
    text: str
    img_urls: List[str] = Field(default_factory=list)
    video_url: Optional[str] = Field(default=None)
    retweet: Optional['WeiboDynamic'] = Field(default=None)
    user: Optional[WeiboUser] = Field(default=None)

    @property
    def url(self) -> str:
        return f"https://m.weibo.cn/status/{self.bid}"