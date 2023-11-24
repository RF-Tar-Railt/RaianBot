import hashlib
import hmac
import json
import time
from typing import Any, Optional, Protocol
from urllib import parse

from httpx import AsyncClient


class SKAutoSignRecord(Protocol):
    id: Any
    token: Any


app_code = "4ca99fa6b56cc2ba"
header = {
    "User-Agent": "Skland/1.4.1 (com.hypergryph.skland; build:100001014; Android 31; ) Okhttp/4.11.0",
    "Accept-Encoding": "gzip",
    "Connection": "close",
}
header_for_sign = {
    "platform": "1",
    "timestamp": "",
    "dId": "de9759a5afaa634f",
    "vName": "1.4.1",
}

# 签到url
sign_url = "https://zonai.skland.com/api/v1/game/attendance"
# 绑定的角色url
binding_url = "https://zonai.skland.com/api/v1/game/player/binding"
# 使用token获得认证代码
grant_code_url = "https://as.hypergryph.com/user/oauth2/v2/grant"
# 使用认证代码获得cred
cred_code_url = "https://zonai.skland.com/api/v1/user/auth/generate_cred_by_code"


def generate_signature(token: str, path, body_or_query):
    """
    获得签名头
    接口地址+方法为Get请求？用query否则用body+时间戳+ 请求头的四个重要参数（dId，platform，timestamp，vName）.toJSON()
    将此字符串做HMAC加密，算法为SHA-256，密钥token为请求cred接口会返回的一个token值
    再将加密后的字符串做MD5即得到sign
    :param token: 拿cred时候的token
    :param path: 请求路径（不包括网址）
    :param body_or_query: 如果是GET，则是它的query。POST则为它的body
    :return: 计算完毕的sign
    """
    # 总是说请勿修改设备时间，怕不是yj你的服务器有问题吧，所以这里特地-2
    t = str(int(time.time()) - 2)
    token = token.encode("utf-8")
    header_ca = header_for_sign.copy()
    header_ca["timestamp"] = t
    header_ca_str = json.dumps(header_ca, separators=(",", ":"))
    s = path + body_or_query + t + header_ca_str
    hex_s = hmac.new(token, s.encode("utf-8"), hashlib.sha256).hexdigest()
    md5 = hashlib.md5(hex_s.encode("utf-8")).hexdigest()
    return md5, header_ca


def get_sign_header(token: str, url: str, method: str, body: Optional[dict], old_header: dict):
    h = old_header.copy()
    p = parse.urlparse(url)
    if method.lower() == "get":
        h["sign"], header_ca = generate_signature(token, p.path, p.query)
    else:
        h["sign"], header_ca = generate_signature(token, p.path, json.dumps(body))
    h.update(header_ca)
    return h


async def bind(token: str) -> tuple[str, str]:
    async with AsyncClient(verify=False, headers=header) as client:
        response = await client.post(grant_code_url, json={"appCode": app_code, "token": token, "type": 0})
        if response.status_code != 200:
            raise RuntimeError(f"获得认证代码失败：{response.status_code}")
        resp = response.json()
        if resp["status"] != 0:
            raise RuntimeError(f'获得认证代码失败：{resp["msg"]}')
        grant_code = resp["data"]["code"]
        response = await client.post(cred_code_url, json={"code": grant_code, "kind": 1})
        resp = response.json()
        if resp["code"] != 0:
            raise RuntimeError(f'获得cred失败：{resp["messgae"]}')
        return resp["data"]["cred"], resp["data"]["token"]

        # if not token and session in self.data:
        #     token = self.data[session].get("origin")
        # if not token:
        #     raise "数据失效！请尝试重新获取 token 来绑定"


async def sign(record: SKAutoSignRecord):
    try:
        cred, token = await bind(record.token)
    except RuntimeError as e:
        yield {"status": False, "text": str(e), "target": ""}
        return
    headers = {
        **header,
        "cred": cred,
    }
    async with AsyncClient(verify=False) as client:
        response = await client.get(binding_url, headers=get_sign_header(token, binding_url, "get", None, headers))
        response = response.json()
        if response["code"] != 0:
            yield {"status": False, "text": f"请求角色列表出现问题：{response['message']}", "target": ""}
            return
        binding = []
        for i in response["data"]["list"]:
            if i.get("appCode") == "arknights":
                binding.extend(i["bindingList"])
        if not binding:
            yield {"status": False, "text": f"{record.id} 未创建方舟账号", "target": ""}
            return
        for i in binding:
            query = {"uid": i["uid"], "gameId": i["channelMasterId"]}
            drname = i["nickName"]
            server = i["channelName"]
            result = {}
            sign_response = await client.post(
                sign_url,
                headers=get_sign_header(token, sign_url, "post", query, headers),
                json=query,
            )
            sign_response = sign_response.json()
            if sign_response.get("code") == 0:
                result["status"] = True
                result["target"] = query["uid"]
                result["text"] = f"{server}账号 {drname}(UID {query['uid']})签到成功\n"
                awards = sign_response.get("data").get("awards")
                for award in awards:
                    result["text"] += "获得的奖励ID为：" + award.get("resource").get("id") + "\n"
                    result["text"] += (
                        "此次签到获得了"
                        + str(award.get("count"))
                        + "单位的"
                        + award.get("resource").get("name")
                        + "("
                        + award.get("resource").get("type")
                        + ")\n"
                    )
                    result["text"] += "奖励类型为：" + award.get("type") + "\n"
            else:
                result["status"] = False
                result["target"] = query["uid"]
                result["text"] = f"{server}账号 {drname}(UID {query['uid']})签到失败:\n" + sign_response.get("message")
            yield result
