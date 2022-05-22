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

## 项目结构

```
RaianBot
├─── data
│   ├─── plugins 
│   │   ├─── weibo_data.json     插件运行时产生的临时文件或缓存数据
│   │   └─── ...
│   ├─── static 
│   │   ├─── ill_templates.json  插件运行时需要的静态资源或数据文件
│   │   └─── ...
│   ├─── __init__.py             机器人数据访问/修改入口
│   ├─── model.py                机器人数据模型
│   ├─── users_data.json         用户数据文件
│   ├─── groups_data.json        群组数据文件
│   └─── cache_data.json         缓存数据文件
├─── modules                     插件依赖的功能库，但没有上传到 pypi等中
│   ├─── gacha                   抽卡功能库
│   ├─── weibo                   微博 api 功能库
│   ├─── rand                    存放随机函数
│   └─── ...
├─── plugins                     机器人插件目录 (可以进配置文件中自行变更)
├─── utils                       工具函数存放目录
│   ├─── simple_permission.py    鉴权接口
│   ├─── generate_img.py         图片生成工具
│   └─── ...             
├─── bot_config.yml              机器人配置文件
├─── config.py                   配置访问接口
├─── main.py                     应用执行入口
├─── requirements.txt            项目运行环境依赖包
├─── README.md                   项目说明文件
└─── ...  
```
