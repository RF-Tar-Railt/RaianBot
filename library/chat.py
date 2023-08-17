import json

from loguru import logger
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tbp.v20190627 import tbp_client, models

class TencentChatBot:
    def __init__(self, name: str, secret_id: str, secret_key: str, bot_id: str, bot_env: str):
        self.name = name
        self.bot_id = bot_id
        self.bot_env = bot_env
        self.cred = credential.Credential(secret_id, secret_key)
        http_prof = HttpProfile(endpoint="tbp.tencentcloudapi.com")
        client_prof = ClientProfile()
        client_prof.httpProfile = http_prof
        self.client = tbp_client.TbpClient(self.cred, "ap-guangzhou", client_prof)

    def chat(self, text: str, session: str):
        try:
            req = models.TextProcessRequest()
            req.from_json_string(
                json.dumps(
                    {
                        "Action": "TextProcess",
                        "Version": "2019-06-27",
                        "BotId": self.bot_id,
                        "BotEnv": self.bot_env,
                        "TerminalId": session,
                        "InputText": text
                    },
                    ensure_ascii=False
                )
            )

            resp = self.client.TextProcess(req)
            if resp.ResponseText:
                msg: str = resp.ResponseText
                nickname: str = self.name
                return msg.replace("小微", nickname)

        except TencentCloudSDKException as err:
            logger.error(repr(err))
            return
