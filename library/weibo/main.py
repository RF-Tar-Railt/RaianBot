import asyncio
from typing import Union, Type, Optional, Dict, Any, Literal, List
import aiohttp
from pyquery import PyQuery as Query
from contextlib import suppress
from .storage import DefaultWeiboData, BaseWeiboData
from .model import WeiboUser, WeiboDynamic
from .exceptions import RespStatusError, RespDataError, RespDataErrnoError, WeiboError


class WeiboAPI:

    user_agent = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) "
        "AppleWebKit/601.1.46 (KHTML, like Gecko) "
        "Version/9.0 Mobile/13B143 Safari/601.1 wechatdevtools/0.7.0 "
        "MicroMessenger/6.3.9 "
        "Language/zh_CN webview/0"
    )

    def __init__(
        self,
        filepath: str,
        storage: Optional[Type[BaseWeiboData]] = None,
    ):
        self.data = (storage or DefaultWeiboData)(filepath)
        self.data.load()
        self.session = aiohttp.ClientSession()

    async def close(self):
        self.data.save()
        await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _call(self, params: dict, timeout: int = 10) -> Optional[Dict[str, Any]]:
        base_url = "https://m.weibo.cn/api/container/getIndex?"
        headers = {
            "Host": "m.weibo.cn",
            "Referer": "https://m.weibo.cn/u/XXX",
            "User-Agent": self.user_agent
        }
        async with self.session.get(base_url, params=params, headers=headers, timeout=timeout) as resp:
            if resp.status != 200:
                raise RespStatusError(f"Error: {resp.status}")
            data = await resp.json()
            if data.get("ok") != 1:
                raise RespDataError(f"Error: {data}")
            if data["data"].get("errno"):
                raise RespDataErrnoError(f"Error: {data['data']['errno']}")
            return data["data"]

    async def search_users(self, target: str) -> List[int]:
        """搜索用户名，返回可能的所有用户的ids"""
        params = {"containerid": f"100103type%3D3%26q%3D{target}%26t%3D0"}
        d_data = await self._call(params)
        return [int(i["user"]["id"]) for i in d_data["cards"][1]["card_group"]]

    async def get_profile(
        self,
        uid: int,
        save: bool = False,
        cache: bool = True,
    ) -> Optional[WeiboUser]:
        if cache and str(uid) in self.data.followers:
            return self.data.followers[str(uid)]
        params = {"type": "uid", "value": uid}
        try:
            d_data = await self._call(params)
        except (WeiboError, asyncio.TimeoutError):
            return
        user = WeiboUser(
            id=uid,
            name=d_data["userInfo"]["screen_name"],
            avatar=d_data["userInfo"]["avatar_hd"],
            statuses=d_data["userInfo"]["statuses_count"],
            visitable=(d_data["tabsInfo"] != []),
            description=d_data["userInfo"]["description"],
        )
        if user.visitable:
            params["containerid"] = user.contain_id("weibo")
            cdata = await self._call(params)
            user.total = cdata["cardlistInfo"]["total"]
        self.data.mapping[user.name] = str(uid)
        if save:
            self.data.followers[str(uid)] = user
            self.data.save()
        return user

    async def get_profile_by_name(
        self,
        name: str,
        index: int = 0,
        save: bool = False,
        cache: bool = True,
    ) -> Optional[WeiboUser]:
        index = max(index, 0)
        if cache and name in self.data.mapping:
            return await self.get_profile(int(self.data.mapping[name]), save, cache)
        return await self.get_profile((await self.search_users(name))[index], save, cache)

    async def get_profiles(self, name: str) -> List[WeiboUser]:
        res = []
        for i in await self.search_users(name):
            if prof := await self.get_profile(i):
                res.append(prof)
        return res


    def _handler_dynamic(self, data: Dict) -> WeiboDynamic:
        text: str = Query(data["text"]).text(squash_space=False) + "\n"
        dynamic = WeiboDynamic(bid=data["bid"], text=text)
        if len(data["pic_ids"]) > 0:
            pics = data["pics"]
            for i in range(len(pics)):
                dynamic.img_urls.append(pics[i]["large"]["url"])
        if (page_info := data.get("page_info")) and page_info["type"] == "video":
            dynamic.img_urls.append(page_info["page_pic"]["url"])
            dynamic.video_url = page_info["urls"]["mp4_720p_mp4"]
        if ret := data.get("retweeted_status"):
            dynamic.retweet = self._handler_dynamic(ret)
        return dynamic

    async def get_dynamic(
        self,
        target: Union[int, WeiboUser],
        keyword: Literal["profile", "weibo", "video", "album"] = "weibo",
        index: int = -1,
        page: int = 1,
        save: bool = False,
        cache: bool = False,
    ) -> Optional[WeiboDynamic]:
        if not isinstance(target, WeiboUser):
            target = await self.get_profile(target, save, cache)
            if not target:
                return
        params = {
            "type": "uid",
            "value": target.id,
            "containerid": target.contain_id(keyword),
            "page": page,
        }
        try:
            d_data = await self._call(params)
        except (WeiboError, asyncio.TimeoutError):
            return
        if index > len(d_data["cards"]) - 1:
            return
        if d_data["cards"][0]["card_type"] != 9:
            return
        if index < 0:
            if len(d_data["cards"]) > 1:
                ids = [int(i["mblog"]["id"]) for i in d_data["cards"] if i["card_type"] == 9]
                index = ids.index(max(ids))
            else:
                index = 0
        res = self._handler_dynamic(d_data["cards"][index]["mblog"])
        res.user = target
        if save:
            target.latest = res.bid
            self.data.followers[str(target.id)] = target
            self.data.save()
        return res

    async def update(self, target: int) -> Optional[WeiboDynamic]:
        profile = await self.get_profile(target)
        if not profile:
            return
        dynamic_total = profile.total
        params = {"type": "uid", "value": profile.id, "containerid": profile.contain_id("weibo")}
        try:
            d_data = await self._call(params)
        except (WeiboError, asyncio.TimeoutError):
            return
        if d_data["cardlistInfo"]["total"] > dynamic_total:
            profile.total = d_data["cardlistInfo"]["total"]
            dy = await self.get_dynamic(profile, save=False)
            if dy.bid == profile.latest:
                return
            profile.latest = dy.bid
            self.data.followers[str(profile.id)] = profile
            self.data.save()
            return dy
        return
