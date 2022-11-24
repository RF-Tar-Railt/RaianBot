from aiohttp import ClientSession
from typing import Optional
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tmt.v20180321 import tmt_client, models
import asyncio


class BaseTrans:
    async def trans(self, content: str, lang: str) -> Optional[str]:
        ...


class TencentTrans(BaseTrans):
    def __init__(self, secret_id: str, secret_key: str):
        self.cred = credential.Credential(secret_id, secret_key)
        self.client = tmt_client.TmtClient(self.cred, "ap-guangzhou")

    async def trans(self, content, target):
        try:
            req = models.TextTranslateRequest()
            req.SourceText = content
            req.Source = 'auto'
            req.Target = target
            req.ProjectId = 0
            resp = self.client.TextTranslate(req).TargetText
            await asyncio.sleep(0.1)
            return resp
        except TencentCloudSDKException:
            return


class YoudaoTrans(BaseTrans):
    @classmethod
    async def trans(cls, content, lang) -> str:
        url = 'http://fanyi.youdao.com/translate?smartresult=dict&smartresult=true'
        data = {'i': content, 'from': 'AUTO', 'to': lang, 'smartresult': 'dict', 'client': 'fanyideskweb',
                'doctype': 'json', 'version': '2.1', 'keyfrom': 'fanyi.web', 'action': 'FY_BY_CLICKBUTTON',
                'typeResult': 'false'}  # zh-CHS
        async with ClientSession() as session:
            async with session.post(url, data=data) as resp:
                result = await resp.json()
                return result['translateResult'][0][0]['tgt']
