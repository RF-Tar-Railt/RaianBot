# RaianBot

`RaianBot` 是基于 `graia-ariadne` 与 `arclet-alconna` 的简易 QQ 机器人 

## 已有功能

- 签到
- 以图搜图
- 获取微博动态
- 方舟公招计算截图
- 天气查询
- 发病
- 随机方舟干员
- 方舟模拟抽卡
- 每日抽签
- 状态获取

## 下载

链接: [link](https://github.com/RF-Tar-Railt/RaianBot/releases/download/v0.4/raian-bot-0.4.0.zip)

## 安装

### 配置环境
解压缩最新的`raian-bot.zip`, 并进入存放有`main.py`的文件夹下

**mirai部分**
1. 确保安装并配置好了`java`环境, 推荐`java17`或`openj9`
2. 解压缩`mcl.zip`

**bot部分**
1. 安装`python`环境，至少要求`python 3.8`及以上版本
2. 命令行输入如下命令: (确保命令行运行在`main.py`文件夹下)

```bash
pip install -r requirements.txt
```

### 配置文件

**mirai部分**
1. 前往`mcl/config/net.mamoe.mirai-api-http`下, 打开`config.yml`文件
2. 修改其中的`verifyKey`, 适当修改`adapterSettings`下的`host`与`port`
3. 前往`mcl/config/Console`下, 打开`AutoLogin.yml`文件
4. 按提示修改其中的`account`与`password`

**bot部分**
1. 打开`bot_config.yml`
2. 按照提示逐个修改. 其中`verify_key`, `host`, `port`应与`config.yml`内的相同

### 运行配置

**mirai部分**
1. 在`mcl`文件夹下双击运行`mcl.cmd`文件
2. 若提示弹窗验证, 请按以下方法操作: [链接](https://docs.mirai.mamoe.net/mirai-login-solver-selenium)
3. 命令框内出现正常对话信息则代表登录成功

**bot部分**
1. 运行`main.py`, 机器人发送提示信息则代表启动成功
2. 根据喜好自行配置`main.py`中的各项初始化配置

## 项目结构

```
RaianBot
├─── app                         机器人功能相关
│   ├─── core.py                 机器人核心代码, 负责统一调度资源
│   ├─── data.py                 机器人数据访问/修改接口
│   ├─── config.py               机器人配置访问接口
│   ├─── logger.py               为log增加文件输出
│   ├─── model.py                机器人数据模型
│   └─── ...
├─── assets
│   ├─── data                    存放插件运行时需要的静态资源或数据文件
│   │   ├─── ill_templates.json  
│   │   └─── ...
│   ├─── image                   存放插件运行时需要图片资源
│   └─── ...
├─── cache                       机器人运行时产生的临时文件或缓存数据
│   ├─── plugins 
│   │   ├─── weibo_data.json     插件运行时产生的临时文件或缓存数据
│   │   └─── ...
│   ├─── users_data.json         用户数据文件
│   ├─── groups_data.json        群组数据文件
│   └─── basic_data.json         基础数据文件
├─── logs                        机器人日志目录
│   ├─── latest.log
│   └─── ...
├─── modules                     插件依赖的功能库，但没有上传到 pypi等中
│   ├─── gacha                   抽卡功能库
│   ├─── weibo                   微博 api 功能库
│   ├─── rand                    存放随机函数
│   └─── ...
├─── plugins                     机器人插件目录 (可以进配置文件中自行变更)
│   └─── ...
├─── utils                       工具函数存放目录
│   ├─── control.py              鉴权接口
│   ├─── generate_img.py         图片生成工具
│   └─── ...             
├─── bot_config.yml              机器人配置文件
├─── main.py                     应用执行入口
├─── requirements.txt            项目运行环境依赖包
├─── README.md                   项目说明文件
└─── ...  
```
