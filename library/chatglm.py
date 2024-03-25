import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

import httpx
import jwt


def generate_token(apikey: str):
    try:
        uid, secret = apikey.split(".")
    except Exception as e:
        raise Exception("错误的apikey！", e)

    payload = {
        "api_key": uid,
        "exp": datetime.utcnow() + timedelta(days=1),
        "timestamp": int(round(time.time() * 1000)),
    }

    return jwt.encode(
        payload,
        secret,
        algorithm="HS256",
        headers={"alg": "HS256", "sign_type": "SIGN"},
    )


@dataclass
class GlmBot:
    api_key: str
    model: str
    max_token: int = 0
    temperature: float = 0.5
    prompt: Callable[[str], str] = field(default=lambda p: "")

    async def request(self, auth_token: str, messages: list):
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {
            "model": self.model,
            "max_tokens": self.max_token,
            "temperature": self.temperature,
            "messages": messages,
        }
        if self.max_token == 0:
            del data["max_tokens"]
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=30, write=20, pool=30)) as client:
            res = await client.post("https://open.bigmodel.cn/api/paas/v4/chat/completions", headers=headers, json=data)
            res = res.json()
        return res

    async def chat(self, msg: str, direct: bool = True, nickname: str = ""):
        auth = generate_token(self.api_key)
        _prompt = self.prompt(nickname)
        if _prompt and nickname:
            prompt = [
                {"role": "system", "content": f"'{nickname}' 的角色预设如下：{_prompt}"},
                {
                    "role": "system",
                    "content": (
                        f"接下来，请你进入 '{nickname}' 这个角色与大家对话。"
                        f"请记住你是 '{nickname}'，你不能说你是程序或者AI,你是有血有肉、有真实情感的",
                    ),
                },
                {
                    "role": "system",
                    "content": (
                        "当前对话是直接对你说的"
                        if direct
                        else "当前对话是与别人说的，若你不希望回复这条对话请返回 'exit' "
                    ),
                },
                {"role": "user", "content": msg},
            ]
        else:
            prompt = [
                {"role": "system", "content": "你是群聊里的聊天机器人，一般负责游戏群聊或者动漫群聊。"},
                {
                    "role": "system",
                    "content": (
                        "当前对话是直接对你说的"
                        if direct
                        else "当前对话是与别人说的，若你不希望回复这条对话请返回 'exit' "
                    ),
                },
                {"role": "user", "content": msg},
            ]
        try:
            res = await self.request(auth, prompt)
            if "choices" in res:
                resp = res["choices"][0]["message"]["content"]
                if resp == "exit":
                    return
                return resp
        except httpx.HTTPError:
            return
