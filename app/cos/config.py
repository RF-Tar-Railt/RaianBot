from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote

from httpx._types import ProxiesTypes


def format_region(region: str, module: str, enable_old_domain: bool, enable_internal_domain: bool):
    """格式化地域"""
    if not isinstance(region, str):
        raise TypeError("region is not string type")
    if not region:
        raise ValueError("region is required not empty!")
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9.\-]*[A-Za-z0-9]$", region):
        raise ValueError("region format is illegal, only digit, letter and - is allowed!")
    if region.find(module) != -1:
        return region  # 传入cos.ap-beijing-1这样显示加上cos.的region
    if region in {
        "cn-north",
        "cn-south",
        "cn-east",
        "cn-south-2",
        "cn-southwest",
        "sg",
    }:
        return region  # 老域名不能加cos.
    #  支持v4域名映射到v5
    # 转换为内部域名 (只有新域名才支持内部域名)
    if not enable_old_domain and enable_internal_domain and module == "cos.":
        module = "cos-internal."

    if region == "cossh":
        return module + "ap-shanghai"
    if region == "cosgz":
        return module + "ap-guangzhou"
    if region == "cosbj":
        return module + "ap-beijing"
    if region == "costj":
        return module + "ap-beijing-1"
    if region == "coscd":
        return module + "ap-chengdu"
    if region == "cossgp":
        return module + "ap-singapore"
    if region == "coshk":
        return module + "ap-hongkong"
    if region == "cosca":
        return module + "na-toronto"
    if region == "cosger":
        return module + "eu-frankfurt"

    return module + region  # 新域名加上cos.


def format_endpoint(endpoint: str, region: str, module: str, enable_old_domain: bool, enable_internal_domain: bool):
    # 客户使用全球加速域名时，只会传endpoint不会传region。此时这样endpointCi和region同时为None，就会报错。
    if not endpoint and not region and module == "cos.":
        raise ValueError("Region or Endpoint is required not empty!")

    """格式化终端域名"""
    if endpoint:
        return endpoint
    elif region:
        region = format_region(region, module, enable_old_domain, enable_internal_domain)
        if enable_old_domain:
            return f"{region}.myqcloud.com"
        else:
            return f"{region}.tencentcos.cn"
    else:
        return None


def format_bucket(bucket: str, appid: str):
    """兼容新老bucket长短命名,appid为空默认为长命名,appid不为空则认为是短命名"""
    if not isinstance(bucket, str):
        raise TypeError("bucket is not string")
    if not bucket:
        raise ValueError("bucket is required not empty")
    if not (re.match(r"^[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9]$", bucket) or re.match("^[A-Za-z0-9]$", bucket)):
        raise ValueError("bucket format is illegal, only digit, letter and - is allowed!")
    # appid为空直接返回bucket
    if not appid:
        return bucket
    if not isinstance(appid, str):
        raise TypeError("appid is not string")
    # appid不为空,检查是否以-appid结尾
    if bucket.endswith("-" + appid):
        return bucket
    return bucket + "-" + appid


@dataclass
class CosConfig:
    region: str
    secret_id: str
    secret_key: str
    appid: str | None = None
    token: str | None = None
    scheme: str | None = None
    timeout: int | None = None
    endpoint: str | None = None
    ip: str | None = None
    port: int | None = None
    ua: str | None = None
    proxies: ProxiesTypes | None = None
    domain: str | None = None
    service_domain: str | None = None
    keep_alive: bool | None = None
    pool_connections: int = 10
    pool_maxsize: int = 10
    follow_redirects: bool = False
    sign_host: bool = True
    endpoint_ci: str | None = None
    endpoint_pic: str | None = None
    enable_old_domain: bool = True
    enable_internal_domain: bool = True
    sign_params: bool = True

    def __post_init__(self):
        self.copy_part_threshold_size = 5 * 1024 * 1024 * 1024

        if self.domain is None:
            self.endpoint = format_endpoint(
                self.endpoint, self.region, "cos.", self.enable_old_domain, self.enable_internal_domain
            )
        if self.scheme is None:
            self.scheme = "https"
        if self.scheme != "http" and self.scheme != "https":
            raise ValueError("Scheme can be only set to http/https")

        # 格式化ci的endpoint 不支持自定义域名的
        # ci暂不支持新域名
        self.endpoint_ci = format_endpoint(self.endpoint_ci, self.region, "ci.", True, False)
        self.endpoint_pic = format_endpoint(self.endpoint_pic, self.region, "pic.", True, False)

        if not self.secret_id or not self.secret_key:
            raise RuntimeError("SecretId and SecretKey is Required!")

    def uri(self, bucket: str, path: str, endpoint: str | None = None, domain: str | None = None):
        """拼接url

        :param bucket: 存储桶名称.
        :param path: 请求COS的路径.
        :param endpoint: 请求COS的路由.
        :param domain: 请求COS的自定义域名.
        :return: 请求COS的URL地址.
        """
        scheme = self.scheme
        # 拼接请求的url,默认使用bucket和endpoint拼接请求域名
        # 使用自定义域名时则使用自定义域名访问
        # 指定ip和port时,则使用ip:port方式访问,优先级最高
        if domain is None:
            domain = self.domain
        if domain is not None:
            url = domain
        else:
            if endpoint is None:
                endpoint = self.endpoint

            if bucket is not None:
                bucket = format_bucket(bucket, self.appid)
                url = f"{bucket}.{endpoint}"
            else:
                url = endpoint
        if self.ip is not None:
            url = self.ip
            if self.port is not None:
                url = f"{self.ip}:{self.port}"

        if path is not None:
            if not path:
                raise ValueError("Key is required not empty")
            if path[0] == "/":
                path = path[1:]
            path = quote(path.encode(), "/-_.~")
            path = path.replace("./", ".%2F")
            request_url = f"{scheme}://{url}/{path}"
        else:
            request_url = f"{scheme}://{url}/"
        return request_url

    def get_host(self, bucket: str):
        """传入bucket名称,根据endpoint获取Host名称
        :param bucket: bucket名称
        :return : Host名称
        """
        return f"{format_bucket(bucket, self.appid)}.{self.endpoint}"

    def set_ip_port(self, ip: str, port: int | None = None):
        """设置直接访问的ip:port,可以不指定Port,http默认为80,https默认为443
        :param ip: 访问COS的ip
        :param port: 访问COS的port
        :return None
        """
        self.ip = ip
        self.port = port
