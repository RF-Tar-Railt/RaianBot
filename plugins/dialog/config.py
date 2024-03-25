from typing import Optional

from pydantic import AnyUrl, Field

from app.config import BasePluginConfig


class Config(BasePluginConfig):
    tencent: bool = Field(default=True)
    """是否使用腾讯云的智能对话服务"""
    open_bigmodel: bool = Field(default=True)
    """是否使用智谱AI开放平台的 chatglm 服务"""
    gpt_api: Optional[AnyUrl] = Field(default=None)
    """gpt-api对话的链接"""


DialogConfig = Config
