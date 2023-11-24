# RaianBot

`RaianBot` 是基于 [`Avilla`](https://github.com/GraiaProject/Avilla) 与 [`Alconna`](https://github.com/ArcletProject/Alconna) 的简易机器人框架 

目前支持平台有 `Mirai`, QQ频道&群全域接口

## 交流反馈

QQ交流：[122680593](https://jq.qq.com/?_wv=1027&k=lhxRkibY)

---

## 目录

+ **[项目结构](#项目结构)**
+ **[已有功能](#已有功能)**
+ **[下载](#下载)**
+ **[安装](#安装)**
  + [配置环境](#配置环境)
  + [配置文件](#配置文件)
  + [运行程序](#运行程序)

---

## 项目结构

```
RaianBot
├─── app                         机器人功能相关
│   ├─── core.py                 机器人核心代码, 负责统一调度资源
│   ├─── config.py               机器人配置访问接口
│   ├─── logger.py               为log增加文件输出
│   ├─── control.py              鉴权接口
│   └─── ...
├─── assets
│   ├─── data                    存放插件运行时需要的静态资源或数据文件
│   │   ├─── ill_templates.json  
│   │   └─── ...
│   ├─── image                   存放插件运行时需要图片资源
│   └─── ...
├─── data                       机器人运行时产生的临时文件或缓存数据
│   ├─── plugins 
│   │   ├─── weibo_data.json     插件运行时产生的临时文件或缓存数据
│   │   └─── ...
│   ├─── data.db                 总数据库
│   └─── ...
├─── config
│   ├─── plugins                 机器人插件的配置目录 (可以在主配置文件中自行变更)
│   │   └─── ...                 各插件的配置 (如需要)
│   └─── config.yml              主配置文件
├─── logs                        机器人日志目录
│   ├─── latest.log
│   └─── ...
├─── library                     插件依赖的功能库，但没有上传到 pypi等中
│   ├─── dice                    骰娘功能库
│   ├─── weibo                   微博 api 功能库
│   ├─── rand                    存放随机函数
│   └─── ...
├─── plugins                     机器人插件目录 (可以在主配置文件中自行变更)
│   └─── ...
├─── main.py                     应用执行入口
├─── requirements.txt            项目运行环境依赖包
├─── README.md                   项目说明文件
└─── ...  
```

## 已有功能

- 聊天对话 （需要适配）
- 管理
- 签到
- 获取微博动态
- 方舟公招计算截图
- 天气查询
- 发病
- 随机方舟干员
- 方舟模拟抽卡
- 每日抽签
- 状态获取
- 跑团掷骰
- 点歌
- 查询干员信息
- 猜干员游戏
- 森空岛自动签到

## 下载

下载压缩包: [link](https://github.com/RF-Tar-Railt/RaianBot/releases/latest)(点击 Assets 下的 raian-bot-XXX)

或 直接使用 git clone:
```shell
git clone https://github.com/RF-Tar-Railt/RaianBot.git
```

## 安装

### 配置环境
解压缩最新的`raian-bot.zip`, 并进入存放有`main.py`的文件夹下

**mirai部分**
1. 确保安装并配置好了`java`环境, 推荐`java17`或`openj9`
2. 前往[`mirai-console-loader`](https://github.com/iTXTech/mirai-console-loader)下载 mcl, 并使用 `mcl -u` 命令更新 `mirai`
, 并在[`mirai-api-http`](https://github.com/project-mirai/mirai-api-http/releases)处下载mirai-api-http.jar(当前bot使用版本为2.9.1), 然后放入`.mcl/plugins/`下
3. 下载 [`mirai-console-dev-qrlogin`](https://github.com/MrXiaoM/mirai-console-dev-qrlogin)，放入`.mcl/plugins/`下

**bot部分**
1. 安装`python`环境，至少要求`python 3.8`及以上版本
2. 命令行输入如下命令: (确保命令行运行在`main.py`文件夹下)

```bash
pip install -r requirements.txt
```

### 配置文件

**mirai部分**
1. 先运行一遍mcl, 以自动生成配置文件, 确认生成后关闭mcl
2. 前往`mcl/config/net.mamoe.mirai-api-http`下, 打开`setting.yml`文件
3. 修改其中的`verifyKey`, 适当修改`adapterSettings`下的`host`与`port`
~~4. 前往`mcl/config/Console`下, 打开`AutoLogin.yml`文件~~
~~5. 按提示修改其中的`account`与`password`~~

**bot部分**
1. bot 的初始配置位于 `./config/` 下
2. 首先更改 `config/config.yml`，按照提示逐个修改. 其中`mirai.verify_key`, `mirai.host`, `mirai.port`应与`mcl/config/net.mamoe.mirai-api-http/setting.yml`内的相同
3. 其次更改 `config/bots/` 下的配置文件，文件名应为 `<bot账号>.yml` (如 "114514.yml")，多个账号则对应多个文件
4. 适当调整各插件的配置文件, 默认位置为 `./config/plugins/`

(或先配置 bot部分，然后运行 `./mah_setting.py`)
### 运行程序

**mirai部分**
1. 在`mcl`文件夹下双击运行`mcl.cmd`文件
2. 在命令框内输入`qrlogin <bot账号>` (如 "qrlogin 114514"), 然后扫描弹出的二维码
~~2. 若提示弹窗验证, 请按以下方法操作: [链接](https://docs.mirai.mamoe.net/mirai-login-solver-selenium)~~
3. 命令框内出现正常对话信息则代表登录成功

**bot部分**

运行`main.py`, 机器人发送提示信息则代表启动成功

