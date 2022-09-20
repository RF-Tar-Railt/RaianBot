from typing import Union, Type, Optional, Dict, Any, Literal
import aiohttp
from contextlib import suppress
from pyquery import PyQuery as Query
from .storage import DefaultWeiboData, BaseWeiboData
from .model import WeiboUser, WeiboDynamic


class WeiboAPI:
    user_agent = (
        'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) '
        'AppleWebKit/601.1.46 (KHTML, like Gecko) '
        'Version/9.0 Mobile/13B143 Safari/601.1 wechatdevtools/0.7.0 '
        'MicroMessenger/6.3.9 '
        'Language/zh_CN webview/0'
    )

    def __init__(
            self,
            filepath: str,
            storage: Optional[Type[BaseWeiboData]] = None,

    ):
        self.data = (storage or DefaultWeiboData)(filepath)
        self.data.load()

    async def _call(self, params: dict, timeout: int = 10) -> Optional[Dict[str, Any]]:
        base_url = 'https://m.weibo.cn/api/container/getIndex?'
        headers = {
            'Host': 'm.weibo.cn',
            'Referer': 'https://m.weibo.cn/u/XXX',
            'User-Agent': self.user_agent
        }
        with suppress(Exception):
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        base_url, params=params, headers=headers, timeout=timeout
                ) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.json()
                    if data.get('ok') != 1:
                        return
                    if data['data'].get('errno'):
                        return
                    return data['data']

    async def search_user(self, target: str) -> Optional[int]:
        """依据用户名返回用户id(str)"""
        if target in self.data.mapping:
            return int(self.data.mapping[target])
        params = {
            'containerid': f'100103type%3D3%26q%3D{target}%26t%3D0'
        }
        if not (d_data := await self._call(params)):
            return
        return int(d_data['cards'][1]['card_group'][0]['user']['id'])

    async def get_profile(
            self,
            target: Union[str, int],
            save: bool = False,
            cache: bool = True,
    ):
        if isinstance(target, str):
            target = await self.search_user(target)
        if cache and str(target) in self.data.followers:
            return self.data.followers[str(target)]
        params = {
            'type': 'uid',
            'value': target
        }
        if not (d_data := await self._call(params)):
            return
        user = WeiboUser(
            id=target,
            name=d_data['userInfo']['screen_name'],
            avatar=d_data['userInfo']['avatar_hd'],
            statuses=d_data['userInfo']['statuses_count'],
            visitable=(d_data['tabsInfo'] != []),
            description=d_data['userInfo']['description']
        )
        if user.visitable:
            params['containerid'] = user.contain_id('weibo')
            if d_data := await self._call(params):
                user.total = d_data['cardlistInfo']['total']
        if save:
            self.data.followers[str(target)] = user
            self.data.mapping[user.name] = str(target)
            await self.data.save()
        return user

    def _handler_dynamic(self, data: Dict) -> WeiboDynamic:
        text: str = Query(data['text']).text(squash_space=False) + '\n'
        dynamic = WeiboDynamic(bid=data['bid'], text=text)
        if len(data['pic_ids']) > 0:
            pics = data['pics']
            for i in range(len(pics)):
                dynamic.img_urls.append(pics[i]['large']['url'])
        if (page_info := data.get('page_info')) and page_info['type'] == 'video':
            dynamic.img_urls.append(page_info['page_pic']['url'])
            dynamic.video_url = page_info['urls']['mp4_720p_mp4']
        if ret := data.get('retweeted_status'):
            dynamic.retweet = self._handler_dynamic(ret)
        return dynamic

    async def get_dynamic(
            self,
            target: Union[str, int, WeiboUser],
            keyword: Literal["profile", "weibo", "video", "album"] = 'weibo',
            index: int = -1,
            page: int = 1,
            save: bool = False,
            cache: bool = False,
    ) -> Optional[WeiboDynamic]:
        if not isinstance(target, WeiboUser):
            if not (target := await self.get_profile(target, save, cache)):
                return
        params = {
            'type': 'uid',
            'value': target.id,
            'containerid': target.contain_id(keyword),
            'page': page,
        }
        if not (d_data := await self._call(params)):
            return
        if index > len(d_data['cards']) - 1:
            return
        if d_data['cards'][0]['card_type'] != 9:
            return
        if index < 0:
            if len(d_data['cards']) > 1:
                ids = [int(i['mblog']['id']) for i in d_data['cards']]
                index = ids.index(max(ids))
            else:
                index = 0
        res = self._handler_dynamic(d_data['cards'][index]['mblog'])
        res.user = target
        if save:
            target.latest = res.bid
            self.data.followers[str(target.id)] = target
            await self.data.save()
        return res

    async def update(
            self,
            target: int
    ) -> Optional[WeiboDynamic]:
        if not (profile := await self.get_profile(target)):
            return
        dynamic_total = profile.total
        params = {
            'type': 'uid',
            'value': profile.id,
            'containerid': profile.contain_id('weibo')
        }
        if not (d_data := await self._call(params)):
            return
        if d_data['cardlistInfo']['total'] > dynamic_total:
            profile.total = d_data['cardlistInfo']['total']
            dy = await self.get_dynamic(profile, save=False)
            if dy.bid == profile.latest:
                return
            profile.latest = dy.bid
            self.data.followers[str(profile.id)] = profile
            await self.data.save()
            return dy
        return
