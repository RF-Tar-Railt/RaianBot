from __future__ import annotations

import base64
import hashlib

import httpx

from .auth import CosS3Auth
from .config import CosConfig

maplist = {
    "ContentLength": "Content-Length",
    "ContentMD5": "Content-MD5",
    "ContentType": "Content-Type",
    "CacheControl": "Cache-Control",
    "ContentDisposition": "Content-Disposition",
    "ContentEncoding": "Content-Encoding",
    "ContentLanguage": "Content-Language",
    "Expires": "Expires",
    "ResponseContentType": "response-content-type",
    "ResponseContentLanguage": "response-content-language",
    "ResponseExpires": "response-expires",
    "ResponseCacheControl": "response-cache-control",
    "ResponseContentDisposition": "response-content-disposition",
    "ResponseContentEncoding": "response-content-encoding",
    "Metadata": "Metadata",
    "ACL": "x-cos-acl",
    "GrantFullControl": "x-cos-grant-full-control",
    "GrantWrite": "x-cos-grant-write",
    "GrantRead": "x-cos-grant-read",
    "StorageClass": "x-cos-storage-class",
    "Range": "Range",
    "IfMatch": "If-Match",
    "IfNoneMatch": "If-None-Match",
    "IfModifiedSince": "If-Modified-Since",
    "IfUnmodifiedSince": "If-Unmodified-Since",
    "CopySourceIfMatch": "x-cos-copy-source-If-Match",
    "CopySourceIfNoneMatch": "x-cos-copy-source-If-None-Match",
    "CopySourceIfModifiedSince": "x-cos-copy-source-If-Modified-Since",
    "CopySourceIfUnmodifiedSince": "x-cos-copy-source-If-Unmodified-Since",
    "VersionId": "versionId",
    "ServerSideEncryption": "x-cos-server-side-encryption",
    "SSEKMSKeyId": "x-cos-server-side-encryption-cos-kms-key-id",
    "SSEKMSContext": "x-cos-server-side-encryption-context",
    "SSECustomerAlgorithm": "x-cos-server-side-encryption-customer-algorithm",
    "SSECustomerKey": "x-cos-server-side-encryption-customer-key",
    "SSECustomerKeyMD5": "x-cos-server-side-encryption-customer-key-MD5",
    "CopySourceSSECustomerAlgorithm": "x-cos-copy-source-server-side-encryption-customer-algorithm",
    "CopySourceSSECustomerKey": "x-cos-copy-source-server-side-encryption-customer-key",
    "CopySourceSSECustomerKeyMD5": "x-cos-copy-source-server-side-encryption-customer-key-MD5",
    "Referer": "Referer",
    "PicOperations": "Pic-Operations",
    "TrafficLimit": "x-cos-traffic-limit",
}


def mapped(headers: dict):
    """S3到COS参数的一个映射"""
    _headers = {}
    for i in headers:
        if i in maplist:
            if i == "Metadata":
                for meta in headers[i]:
                    _headers[meta] = headers[i][meta]
            else:
                _headers[maplist[i]] = headers[i]
        else:
            raise ValueError("No Parameter Named " + i + " Please Check It")
    return _headers


def get_content_md5(body: bytes | str):
    """计算md5值"""
    m2 = hashlib.md5(body.encode() if isinstance(body, str) else body)
    MD5 = base64.standard_b64encode(m2.digest())
    return MD5


async def send_request(
    config: CosConfig,
    method: str,
    url: str,
    bucket: str,
    timeout=30,
    ci_request=False,
    auth: CosS3Auth | None = None,
    data: bytes | str | None = None,
    headers: dict[str, str] | None = None,
    **kwargs,
):
    """封装request库发起http请求"""
    headers = headers or {}
    if config.timeout is not None:  # 用户自定义超时时间
        timeout = config.timeout
    if config.ua is not None:
        headers["User-Agent"] = config.ua
    else:
        headers["User-Agent"] = "cos-python-sdk-v5.1.9.26"
    if config.token is not None:
        if ci_request:
            headers["x-ci-security-token"] = config.token
        else:
            headers["x-cos-security-token"] = config.token
    if config.ip is not None:  # 使用IP访问时需要设置请求host
        if config.domain is not None:
            headers["Host"] = config.domain
        elif bucket is not None:
            headers["Host"] = config.get_host(bucket)
    if config.keep_alive is False:
        headers["Connection"] = "close"
    _headers = {k: v.encode() for k, v in headers.items() if v is not None}
    if config.ip is not None and config.scheme == "https":
        kwargs["verify"] = False
    if config.follow_redirects is not None:
        kwargs["follow_redirects"] = config.follow_redirects
    async with httpx.AsyncClient(proxies=config.proxies, timeout=timeout, **kwargs) as client:
        res = await client.request(
            method,
            url,
            content=data,
            headers=_headers,
            auth=auth,
        )
        if res.status_code < 400:  # 2xx和3xx都认为是成功的
            return res
        raise ValueError(res, res.headers, res.content)


async def put_object(
    config: CosConfig,
    bucket: str,
    body: bytes | str,
    key: str,
    enable_md5=False,
    headers: dict[str, str] | None = None,
):
    headers = mapped(headers or {})
    url = config.uri(bucket=bucket, path=key)
    if enable_md5:
        md5_str = get_content_md5(body)
        if md5_str:
            headers["Content-MD5"] = md5_str
    return await send_request(
        config,
        method="PUT",
        url=url,
        bucket=bucket,
        auth=CosS3Auth(
            config.secret_id,
            config.secret_key,
            False,
            config.sign_host,
            config.sign_params,
            key=key,
        ),
        data=body,
        headers=headers,
    )
