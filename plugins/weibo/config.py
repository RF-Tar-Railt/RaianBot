from app.config import BasePluginConfig


class Config(BasePluginConfig, domain="global"):
    dynamic_forward: bool = False
    """动态推送是否使用合并转发"""


WeiboConfig = Config
