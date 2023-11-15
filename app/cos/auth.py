from __future__ import annotations
import hashlib
import hmac
import time
from urllib.parse import quote, urlparse
from httpx import Request


def filter_headers(r: Request):
    """只设置host content-type 还有x开头的头部.

    :param r: 请求体.
    """
    valid_headers = [
        "cache-control",
        "content-disposition",
        "content-encoding",
        "content-type",
        "content-md5",
        "content-length",
        "expect",
        "expires",
        "host",
        "if-match",
        "if-modified-since",
        "if-none-match",
        "if-unmodified-since",
        "origin",
        "range",
        "transfer-encoding",
    ]
    for i in list(r.headers.keys()):
        if i.lower() in valid_headers:
            continue
        if i.lower().startswith("x-cos-"):
            continue
        del r.headers[i]


class CosS3Auth:
    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        anonymous: bool = False,
        sign_host: bool = False,
        sign_params: bool = False,
        key: str | None = None,
        params=None,
        expire=10000,
    ):
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.anonymous = anonymous
        self._expire = expire
        self._params = params or {}
        self._sign_params = sign_params

        self._sign_host = sign_host

        if key:
            if key[0] == "/":
                self._path = key
            else:
                self._path = "/" + key
        else:
            self._path = "/"

    def __call__(self, r: Request) -> Request:
        # 匿名请求直接返回
        if self.anonymous:
            r.headers["Authorization"] = ""
            return r

        path = self._path
        uri_params = {}
        if self._sign_params:
            uri_params = self._params
        filter_headers(r)

        # 如果headers中不包含host头域，则从url中提取host，并且加入签名计算
        if self._sign_host:
            # 判断headers中是否包含host头域
            contain_host = False
            for i in r.headers:
                if i.lower() == "host":  # 兼容host/Host/HOST等
                    contain_host = True
                    break

            # 从url中提取host
            if not contain_host:
                url_parsed = urlparse(str(r.url))
                if url_parsed.hostname is not None:
                    r.headers["host"] = url_parsed.hostname

        headers = {
            quote(k.encode(), "-_.~").lower(): quote(v.encode(), "-_.~") for k, v in r.headers.items()
        }
        uri_params = {
            quote(k.encode(), "-_.~").lower(): quote(v.encode(), "-_.~") for k, v in uri_params.items()
        }
        formatted = (
            f"{r.method.lower()}\n"
            f"{path}\n"
            f"{'&'.join(map(lambda tupl: f'{tupl[0]}={tupl[1]}', sorted(uri_params.items())))}\n"
            f"{'&'.join(map(lambda tupl: f'{tupl[0]}={tupl[1]}', sorted(headers.items())))}\n"
        )

        start_sign_time = int(time.time())
        sign_time = f"{start_sign_time - 60};{start_sign_time + self._expire}"
        sha1 = hashlib.sha1()
        sha1.update(formatted.encode())

        str_to_sign = f"sha1\n{sign_time}\n{sha1.hexdigest()}\n"
        sign_key = hmac.new(self.secret_key.encode(), sign_time.encode(), hashlib.sha1).hexdigest()
        sign = hmac.new(sign_key.encode(), str_to_sign.encode(), hashlib.sha1).hexdigest()

        r.headers["Authorization"] = (
            f"q-sign-algorithm=sha1"
            f"&q-ak={self.secret_id}"
            f"&q-sign-time={sign_time}"
            f"&q-key-time={sign_time}"
            f"&q-header-list={';'.join(sorted(r.headers.keys()))}"
            f"&q-url-param-list={';'.join(sorted(uri_params.keys()))}"
            f"&q-signature={sign}"
        )
        return r
