from pydantic import BaseModel, Field, AnyUrl
from typing import Optional


class Config(BaseModel):
    nickname: str
    """对话的触发词前缀"""
    tencent: bool = Field(default=True)
    """是否使用腾讯云的翻译服务"""
    gpt_api: Optional[AnyUrl] = Field(default=None)
    """gpt-api对话的链接"""


DialogConfig = Config
