from pathlib import Path
from loguru import logger
from yaml import safe_load

origin = """\
adapters:
  - http
  - ws

## 是否开启认证流程, 若为 true 则建立连接时需要验证 verifyKey
## 建议公网连接时开启
enableVerify: true
verifyKey: {key}

## 开启一些调式信息
debug: false

## 是否开启单 session 模式, 若为 true，则自动创建 session 绑定 console 中登录的 bot
## 开启后，接口中任何 sessionKey 不需要传递参数
## 若 console 中有多个 bot 登录，则行为未定义
## 确保 console 中只有一个 bot 登陆时启用
singleMode: false

## 历史消息的缓存大小
## 同时，也是 http adapter 的消息队列容量
cacheSize: 4096

## adapter 的单独配置，键名与 adapters 项配置相同
adapterSettings:
  ## 详情看 http adapter 使用说明 配置
  http:
    host: {host}
    port: {port}
    cors: [*]
  
  ## 详情看 websocket adapter 使用说明 配置
  ws:
    host: {host}
    port: {port}
    reservedSyncId: -1
"""

mcl_dir_root = Path(input("输入 mcl 的目录: >>>"))
if not mcl_dir_root.exists():
    logger.warning("未知的目录")
    exit(1)
bot_config_dir_root = Path(input("输入 bot 的配置目录，默认为 config: >>>") or "config")
if not bot_config_dir_root.exists():
    logger.warning("未知的目录")
    exit(1)
setting_file = mcl_dir_root / "config" / "net.mamoe.mirai-api-http" / "setting.yml"
setting_file.parent.mkdir(parents=True, exist_ok=True)
config_file = bot_config_dir_root / "config.yml"

with config_file.open("r", encoding='utf-8') as f:
    config_data = safe_load(f)

with setting_file.open("w+", encoding='utf-8') as f:
    f.write(
        origin.format(
            host=config_data['mirai']['host'],
            port=config_data['mirai']['port'],
            key=config_data['mirai']['verify_key']
        )
    )


