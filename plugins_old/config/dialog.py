from typing import Optional
from app.config import BasePluginConfig
from pydantic import Field, AnyUrl


class Config(BasePluginConfig):
    nickname: str
    """对话的触发词前缀"""
    tencent: bool = Field(default=True)
    """是否使用腾讯云的翻译服务"""
    gpt_api: Optional[AnyUrl] = Field(default=None)
    """gpt-api对话的链接"""


DialogConfig = Config
