from typing import Union, Type, Optional, Dict, Any, Tuple
import aiohttp
from graia.ariadne.message.element import Image
from graia.ariadne.message.chain import MessageChain
from pyquery import PyQuery as Query
from .storage import DefaultWeiboData, BaseWeiboData
from .model import WeiboProfile


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

    async def _weibo_call(self, params: dict):
        host = 'm.weibo.cn'
        base_url = 'https://%s/api/container/getIndex?' % host
        headers = {
            'Host': host,
            'Referer': 'https://m.weibo.cn/u/XXX',
            'User-Agent': self.user_agent
        }
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url=base_url, headers=headers, data=params) as resp:
                    return await resp.json()
            except Exception:
                return

    async def get_info(self, uid: Union[str, int], contain: int, page: int = 1):
        params = {
            'type': 'uid',
            'value': str(uid),
            'containerid': contain,
            'page': page
        }
        if not (d_data := await self._weibo_call(params)) or d_data['ok'] != 1:
            return
        return d_data

    async def get_profile(self, target: Union[int, str]) -> Optional[WeiboProfile]:
        if isinstance(target, str):
            if target not in self.data.mapping:
                params = {
                    'containerid': f'100103type%3D3%26q%3D{target}%26t%3D0'
                }
                if not (d_data := await self._weibo_call(params)) or d_data['ok'] != 1:
                    return
                target = int(d_data['data']['cards'][1]['card_group'][0]['user']['id'])
            else:
                target = self.data.mapping[target]
        if str(target) not in self.data.followers:
            params = {
                'type': 'uid',
                'value': target
            }
            if not (d_data := await self._weibo_call(params)) or d_data['ok'] != 1:
                return
            follower_name = d_data['data']['userInfo']['screen_name']
            container_id = d_data['data']['tabsInfo']['tabs'][1]['containerid']
            if not (d_data1 := await self.get_info(target, container_id)):
                return
            total = d_data1['data']['cardlistInfo']['total']
            profile = WeiboProfile.parse_obj(
                {'name': follower_name, 'id': str(target), 'total': total}
            )
            self.data.followers[str(target)] = profile
            self.data.mapping[follower_name] = str(target)
        return self.data.followers[str(target)]

    async def get_dynamic(
            self,
            name: str,
            index: int = -1
    ) -> Optional[Tuple[MessageChain, MessageChain]]:
        profile = await self.get_profile(name)
        if not (d_data := await self.get_info(profile.id, int(profile.contain_id))):
            return
        dynamic_list = []
        if index < 0:
            may_top_id = int(d_data['data']['cards'][0]['mblog']['id'])
            may_last_id = int(d_data['data']['cards'][1]['mblog']['id'])
            index = 0 if may_top_id > may_last_id else 1
        url: str = d_data['data']['cards'][index]['scheme']
        mblog: Dict[str, Any] = d_data['data']['cards'][index]['mblog']
        text = Query(mblog['text']).text()
        dynamic_list.append(text)
        if len(mblog['pic_ids']) > 0:
            pics = mblog['pics']
            for i in range(len(pics)):
                dynamic_list.append(Image(url=pics[i]['large']['url']))
        page_info = mblog.get('page_info')
        if page_info and page_info['type'] == 'video':
            dynamic_list.append(Image(url=page_info['page_pic']['url']))
        self.data.save()
        return (
            MessageChain.create(*dynamic_list),
            MessageChain.create(url)
        )

    async def update(self, name: str) -> Optional[Tuple[MessageChain, MessageChain]]:
        profile = await self.get_profile(name)
        dynamic_total = profile.total
        if not (d_data := await self.get_info(profile.id, int(profile.contain_id))):
            return
        if d_data['data']['cardlistInfo']['total'] > dynamic_total:
            profile.total = d_data['data']['cardlistInfo']['total']
            return await self.get_dynamic(name)
