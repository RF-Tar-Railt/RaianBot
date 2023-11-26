from __future__ import annotations

import json
from dataclasses import dataclass

from httpx import AsyncClient, Request
from httpx._types import ProxiesTypes
from loguru import logger

from .model import HttpProfile
from .sign import signature


@dataclass
class TencentCloudApi:
    secret_id: str
    secret_key: str
    region: str = "ap-guangzhou"
    proxy: ProxiesTypes | None = None

    async def chat(self, text: str, session: str, bot_id: str, bot_env: str, name: str | None = None):
        http = HttpProfile(endpoint="tbp.tencentcloudapi.com")
        async with AsyncClient(proxies=self.proxy) as client:
            params = {
                "BotId": bot_id,
                "BotEnv": bot_env,
                "TerminalId": session,
                "InputText": text,
            }
            action = "TextProcess"
            if http.method == "GET":
                req = Request(http.method, http.url, params=params, headers={})
            elif http.method == "POST":
                req = Request(http.method, http.url, json=params, headers={})
            else:
                raise NotImplementedError(http.method)
            signature(
                self.secret_id,
                self.secret_key,
                action,
                req,
                http,
                {"api_version": "2019-06-27", "service": "tbp", "region": self.region},
            )
            try:
                resp = (await client.send(req)).json()
                if message := resp.get("Response", {}).get("ResponseText"):
                    return message.replace("小微", name) if name else message
                logger.warning(resp)
            except Exception as e:
                logger.error(repr(e))
                return

    async def send_email(
        self,
        addr: str,
        target: list[str],
        subject: str,
        template_id: str,
        template_data: dict[str, str],
        name: str | None = None,
    ):
        http = HttpProfile(endpoint="ses.tencentcloudapi.com")
        async with AsyncClient(proxies=self.proxy) as client:
            params = {
                "FromEmailAddress": f"{name} <{addr}>" if name else addr,
                "Destination": target,
                "Subject": subject,
                "ReplyToAddresses": addr,
                "Template": {"TemplateID": template_id, "TemplateData": json.dumps(template_data, ensure_ascii=False)},
            }
            action = "SendEmail"
            if http.method == "GET":
                req = Request(http.method, http.url, params=params, headers={})
            elif http.method == "POST":
                req = Request(http.method, http.url, json=params, headers={})
            else:
                raise NotImplementedError(http.method)
            signature(
                self.secret_id,
                self.secret_key,
                action,
                req,
                http,
                {"api_version": "2020-10-02", "service": "ses", "region": self.region},
            )
            try:
                resp = (await client.send(req)).json()
                return resp
            except Exception as e:
                logger.error(repr(e))
                return

    async def translate(self, text: str, lang_target: str, lang_source: str = "auto"):
        """
        source:
            auto：自动识别（识别为一种语言）
            zh：简体中文
            zh-TW：繁体中文
            en：英语
            ja：日语
            ko：韩语
            fr：法语
            es：西班牙语
            it：意大利语
            de：德语
            tr：土耳其语
            ru：俄语
            pt：葡萄牙语
            vi：越南语
            id：印尼语
            th：泰语
            ms：马来西亚语
            ar：阿拉伯语
            hi：印地语
        target:
            zh（简体中文）：en（英语）、ja（日语）、ko（韩语）、fr（法语）、es（西班牙语）、it（意大利语）、de（德语）、tr（土耳其语）、ru（俄语）、pt（葡萄牙语）、vi（越南语）、id（印尼语）、th（泰语）、ms（马来语）
        """
        http = HttpProfile(endpoint="tmt.tencentcloudapi.com")
        async with AsyncClient(proxies=self.proxy) as client:
            params = {
                "SourceText": text,
                "Source": lang_source,
                "Target": lang_target,
                "ProjectId": 0,
            }
            action = "TextTranslate"
            if http.method == "GET":
                req = Request(http.method, http.url, params=params, headers={})
            elif http.method == "POST":
                req = Request(http.method, http.url, json=params, headers={})
            else:
                raise NotImplementedError(http.method)
            signature(
                self.secret_id,
                self.secret_key,
                action,
                req,
                http,
                {"api_version": "2018-03-21", "service": "tmt", "region": self.region},
            )
            try:
                resp = (await client.send(req)).json()
                if res := resp.get("Response", {}).get("TargetText"):
                    return res
                logger.warning(resp)
            except Exception as e:
                logger.error(repr(e))
                return
