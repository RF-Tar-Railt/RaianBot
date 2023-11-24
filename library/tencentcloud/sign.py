from __future__ import annotations

import binascii
import hashlib
import hmac
import time
from datetime import datetime

from httpx import Request

from .model import HttpProfile

_json_content = "application/json"
_multipart_content = "multipart/form-data"
_form_urlencoded_content = "application/x-www-form-urlencoded"
_octet_stream = "application/octet-stream"


def sign_normal(secret_key: str, sign_str: str, sign_method: str):
    sign_bytes = bytes(sign_str, "utf-8")
    secret_key = bytes(secret_key, "utf-8")

    if sign_method == "HmacSHA256":
        digestmod = hashlib.sha256
    elif sign_method == "HmacSHA1":
        digestmod = hashlib.sha1
    else:
        raise ValueError("signMethod only support (HmacSHA1, HmacSHA256)")

    hashed = hmac.new(secret_key, sign_bytes, digestmod)
    base64 = binascii.b2a_base64(hashed.digest())[:-1]
    return base64.decode()


def sign_tc3(secret_key: str, date: str, service: str, str2sign: str):
    def _hmac_sha256(key, msg):
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256)

    def _get_signature_key(key, _date, _service):
        k_date = _hmac_sha256(("TC3" + key).encode("utf-8"), _date)
        k_service = _hmac_sha256(k_date.digest(), _service)
        k_signing = _hmac_sha256(k_service.digest(), "tc3_request")
        return k_signing.digest()

    signing_key = _get_signature_key(secret_key, date, service)
    return _hmac_sha256(signing_key, str2sign).hexdigest()


def get_tc3_signature(secret_key: str, req: Request, date: str, service: str):
    canonical_uri = "/"
    canonical_querystring = ""
    payload = req.content

    if req.method == "GET":
        canonical_querystring = req.content.decode()
        payload = b""

    if req.headers.get("X-TC-Content-SHA256") == "UNSIGNED-PAYLOAD":
        payload = b"UNSIGNED-PAYLOAD"

    payload_hash = hashlib.sha256(payload).hexdigest()

    canonical_headers = f"content-type:{req.headers['Content-Type']}\nhost:{req.headers['Host']}\n"
    signed_headers = "content-type;host"
    canonical_request = (
        f"{req.method}\n"
        f"{canonical_uri}\n"
        f"{canonical_querystring}\n"
        f"{canonical_headers}\n"
        f"{signed_headers}\n"
        f"{payload_hash}"
    ).encode()

    algorithm = "TC3-HMAC-SHA256"
    credential_scope = date + "/" + service + "/tc3_request"
    digest = hashlib.sha256(canonical_request).hexdigest()
    string2sign = f"{algorithm}\n{req.headers['X-TC-Timestamp']}\n{credential_scope}\n{digest}"

    return sign_tc3(secret_key, date, service, string2sign)


def signature(secret_id: str, secret_key: str, action: str, req: Request, http: HttpProfile, options: dict[str, str]):
    content_type = _form_urlencoded_content
    if req.method == "GET":
        content_type = _form_urlencoded_content
    elif req.method == "POST":
        content_type = _json_content
    options = options or {}
    if options.get("IsMultipart"):
        content_type = _multipart_content
    if options.get("IsOctetStream"):
        content_type = _octet_stream
    req.headers["Content-Type"] = content_type

    if req.method == "GET" and content_type == _multipart_content:
        raise ValueError("Invalid request method GET for multipart.")

    endpoint = http.endpoint
    timestamp = int(time.time())
    req.headers["Host"] = endpoint
    req.headers["X-TC-Action"] = action[0].upper() + action[1:]
    req.headers["X-TC-RequestClient"] = "SDK_PYTHON_3.0.1034"
    req.headers["X-TC-Timestamp"] = str(timestamp)
    req.headers["X-TC-Version"] = options["api_version"]
    req.headers["X-TC-Region"] = options.get("region", "ap-guangzhou")

    service = options["service"]
    date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")
    sign = get_tc3_signature(secret_key, req, date, service)

    auth = (
        f"TC3-HMAC-SHA256 Credential={secret_id}/{date}/{service}/tc3_request, "
        f"SignedHeaders=content-type;host, Signature={sign}"
    )
    req.headers["Authorization"] = auth
