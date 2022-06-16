from typing import Union, Type, Optional, Dict, Any, Tuple, List
import aiohttp
from pyquery import PyQuery as Query
from .storage import DefaultWeiboData, BaseWeiboData
from .model import WeiboUser


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
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, headers=headers, timeout=timeout) as resp:
                if resp.status != 200:
                    return
                data = await resp.json()
                if data.get('ok') == 1:
                    return data

    async def search_user(self, target: str):
        if target in self.data.mapping:
            return self.data.mapping[target]
        params = {
            'containerid': f'100103type%3D3%26q%3D{target}%26t%3D0'
        }
        if not (d_data := await self._call(params)):
            return
        uid = int(d_data['data']['cards'][1]['card_group'][0]['user']['id'])
    # async def get_info(self, uid: Union[str, int], contain: int, page: int = 1):
    #     params = {
    #         'type': 'uid',
    #         'value': str(uid),
    #         'containerid': contain,
    #         'page': page
    #     }
    #     if not (d_data := await self._weibo_call(params)) or d_data['ok'] != 1:
    #         return
    #     return d_data
    #
    # async def get_profile(
    #         self,
    #         target: Union[int, str],
    #         save: bool = True
    # ) -> Optional[WeiboUser]:
    #     if isinstance(target, str):
    #         if target not in self.data.mapping:
    #             params = {
    #                 'containerid': f'100103type%3D3%26q%3D{target}%26t%3D0'
    #             }
    #             if not (d_data := await self._weibo_call(params)) or d_data['ok'] != 1:
    #                 return
    #             target = int(d_data['data']['cards'][1]['card_group'][0]['user']['id'])
    #         else:
    #             target = self.data.mapping[target]
    #     if str(target) not in self.data.followers:
    #         params = {
    #             'type': 'uid',
    #             'value': target
    #         }
    #         if not (d_data := await self._weibo_call(params)) or d_data['ok'] != 1:
    #             return
    #         follower_name = d_data['data']['userInfo']['screen_name']
    #         container_id = d_data['data']['tabsInfo']['tabs'][1]['containerid']
    #         if not (d_data1 := await self.get_info(target, container_id)):
    #             return
    #         total = d_data1['data']['cardlistInfo']['total']
    #         profile = WeiboUser.parse_obj(
    #             {'name': follower_name, 'id': str(target), 'total': total}
    #         )
    #         if not save:
    #             return profile
    #         self.data.followers[str(target)] = profile
    #         self.data.mapping[follower_name] = str(target)
    #         await self.data.save()
    #     return self.data.followers[str(target)]
    #
    # async def get_dynamic(
    #         self,
    #         target: Union[str, WeiboUser],
    #         index: int = -1,
    #         save: bool = False
    # ) -> Optional[Tuple[str, List[str], str]]:
    #     if isinstance(target, str):
    #         if not (target := await self.get_profile(target, save)):
    #             return
    #     if not (d_data := await self.get_info(target.id, int(target.contain_id))):
    #         return
    #     dynamic_list = []
    #     if index > d_data['data']['cardlistInfo']['total']:
    #         raise ValueError
    #     if index < 0:
    #         may_top_id = int(d_data['data']['cards'][0]['mblog']['id'])
    #         may_last_id = int(d_data['data']['cards'][1]['mblog']['id'])
    #         index = 0 if may_top_id > may_last_id else 1
    #     url: str = d_data['data']['cards'][index]['scheme']
    #     mblog: Dict[str, Any] = d_data['data']['cards'][index]['mblog']
    #     text: str = Query(mblog['text']).text(squash_space=False)
    #     if len(mblog['pic_ids']) > 0:
    #         pics = mblog['pics']
    #         for i in range(len(pics)):
    #             dynamic_list.append(pics[i]['large']['url'])
    #     page_info = mblog.get('page_info')
    #     if page_info and page_info['type'] == 'video':
    #         dynamic_list.append(page_info['page_pic']['url'])
    #     if save:
    #         await self.data.save()
    #     return text, dynamic_list, url
    #
    # async def update(self, target: int) -> Optional[Tuple[str, List[str], str]]:
    #     if not (profile := await self.get_profile(target)):
    #         return
    #     dynamic_total = profile.total
    #     if not (d_data := await self.get_info(profile.id, int(profile.contain_id))):
    #         return
    #     if d_data['data']['cardlistInfo']['total'] > dynamic_total:
    #         profile.total = d_data['data']['cardlistInfo']['total']
    #         return await self.get_dynamic(profile, save=True)
