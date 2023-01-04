from typing import Optional
from app.config import BasePluginConfig
from pydantic import Field


class Config(BasePluginConfig):
    mute_max: int = Field(default=5)
    """允许的最多禁言恢复剩余次数"""
    announcement_title: str = Field(default="来自管理者的公告")
    """公告的标题"""
    enable_fetch_flash: bool = Field(default=False)
    """是否启用闪照截取功能"""
    check_group_in_start: bool = Field(default=True)
    """是否启动后进行检查"""
    enable_member_report: bool = Field(default=True)
    """是否启用户相关事件"""
    member_join_welcome: Optional[str] = Field(default=None)
    """用户入群时的欢迎词"""
    enable_request_handle: bool = Field(default=True)
    """是否启用好友或入群申请处理"""


AdminConfig = Config
