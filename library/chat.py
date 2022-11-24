import json
import random

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.nlp.v20190408 import models, nlp_client


class TencentChatBot:
    def __init__(self, name: str, secret_id: str, secret_key: str):
        self.name = name
        self.cred = credential.Credential(secret_id, secret_key)
        http_prof = HttpProfile(endpoint="nlp.tencentcloudapi.com")
        client_prof = ClientProfile()
        client_prof.httpProfile = http_prof
        self.client = nlp_client.NlpClient(self.cred, "ap-guangzhou", client_prof)

    def chat(self, text: str):
        def error_handle(t):
            return random.choice([
                t, t, t, t,
                "我现在还不太明白你在说什么呢，但没关系，以后的我会变得更强呢！",
                "我有点看不懂你的意思呀，可以跟我聊些简单的话题嘛",
                "其实我不太明白你的意思...",
                "抱歉哦，我现在的能力还不能够明白你在说什么，但我会加油的～",
            ])

        try:
            req = models.ChatBotRequest()
            req.from_json_string(json.dumps({"Query": text}, ensure_ascii=False))

            resp = self.client.ChatBot(req)
            if resp.Reply:
                msg: str = resp.Reply
                nickname: str = self.name
                msg = msg.replace("腾讯小龙女", nickname).replace("小龙女", nickname)
                return msg
            return error_handle(text)
        except TencentCloudSDKException as e:
            print(e)
            return error_handle(text)
