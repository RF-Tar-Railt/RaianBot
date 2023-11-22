from typing import Optional

from aiohttp import ClientSession

from .tencentcloud import TencentCloudApi


class BaseTrans:
    async def trans(self, content: str, lang: str) -> Optional[str]:
        ...


class TencentTrans(BaseTrans):
    def __init__(self, secret_id: str, secret_key: str):
        self.api = TencentCloudApi(secret_id, secret_key)

    async def trans(self, content, lang):
        return await self.api.translate(content, lang)


class YoudaoTrans(BaseTrans):
    @classmethod
    async def trans(cls, content, lang) -> str:
        url = "http://fanyi.youdao.com/translate?smartresult=dict&smartresult=true"
        data = {
            "i": content,
            "from": "AUTO",
            "to": lang,
            "smartresult": "dict",
            "client": "fanyideskweb",
            "doctype": "json",
            "version": "2.1",
            "keyfrom": "fanyi.web",
            "action": "FY_BY_CLICKBUTTON",
            "typeResult": "false",
        }  # zh-CHS
        async with ClientSession() as session:
            async with session.post(url, data=data) as resp:
                result = await resp.json()
                return result["translateResult"][0][0]["tgt"]
