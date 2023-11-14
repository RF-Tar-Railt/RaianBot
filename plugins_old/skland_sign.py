import re
import asyncio
from app import RaianBotService, RaianBotInterface, Sender, Target, accessable, exclusive, record, logger, render_markdown
from arclet.alconna import  Alconna, Args, CommandMeta, Option
from arclet.alconna.graia import Match, alcommand, assign
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image
from graia.ariadne.event.lifecycle import ApplicationShutdown
from graiax.shortcut.saya import crontab, listen, every
from library.skland_autosign import SKAutoSign


alc = Alconna(
    "森空岛签到",
    Option("绑定", Args["token", str]["uid;?#特定用户", str]),
    Option("解除", Args["uid;?#特定用户", str]),
    Option("查询", Args["uid;?#特定用户", str]),
    Option("方法"),
    meta=CommandMeta(
        "森空岛方舟自动签到",
        usage="""\
每天 0:30 开始自动签到，若与绑定者为好友则同时会私聊通知签到结果

**token获取方法**：在森空岛官网登录后，根据你的服务器，选择复制以下网址中的内容

官服：https://web-api.skland.com/account/info/hg

B服：https://web-api.skland.com/account/info/ak-b

***请在浏览器中获取token，避免在QQ打开的网页中获取，否则可能获取无效token***

再通过 ’渊白森空岛签到   绑定   你从网址里获取的token或者内容‘ 命令来绑定

**注意空格！！！**
""",
        example="""\
$森空岛签到 方法
$绑定森空岛签到    token1234
$森空岛签到 绑定   token1234
$解除森空岛签到
$森空岛签到结果
"""
    ),
)
alc.shortcut("绑定森空岛签到", {"command": MessageChain(f"{alc.prefixes[0]}森空岛签到 绑定")})
alc.shortcut("解除森空岛签到", {"command": MessageChain(f"{alc.prefixes[0]}森空岛签到 解除")})
alc.shortcut("解除(\d+)森空岛签到", {"command": MessageChain(f"{alc.prefixes[0]}森空岛签到 解除"), "args": ["{0}"]})
alc.shortcut("$森空岛签到结果", {"command": MessageChain(f"{alc.prefixes[0]}森空岛签到 查询")})
alc.shortcut("$(\d+)森空岛签到结果", {"command": MessageChain(f"{alc.prefixes[0]}森空岛签到 查询"), "args": ["{0}"]})

bot = RaianBotService.current()
api = SKAutoSign(f"{bot.config.plugin_cache_dir / 'skautosign.json'}")


@alcommand(alc)
@assign("方法")
@record("森空自动签到")
@exclusive
@accessable
async def notice(app: Ariadne, sender: Sender):
    return await app.send_message(sender, Image(data_bytes=await render_markdown(alc.meta.usage)))

@alcommand(alc)
@assign("绑定")
@record("森空自动签到")
@exclusive
@accessable
async def reg(app: Ariadne, sender: Sender, target: Target, token: Match[str], uid: Match[str]):
    session = str(target.id)
    if "content" in token.result:
        token.result = re.match(".*content(\")?:(\")?(?P<token>[^{}\"]+).*", token.result)["token"]
    try:
        await api.bind(session, token.result, uid.result if uid.available else "")
    except RuntimeError as e:
        return await app.send_message(sender, str(e))
    except KeyError:
        return await app.send_message(sender, """
参数错误！
请检查你的token是否正确
以及是否登录了森空岛官网
""")
    return await app.send_message(sender, "森空岛自动签到录入成功")

@alcommand(alc)
@assign("解除")
@record("森空自动签到")
@exclusive
@accessable
async def rm(app: Ariadne, sender: Sender, target: Target, uid: Match[str]):
    session = str(target.id)
    if session not in api.data:
        return await app.send_message(sender, "未绑定森空岛自动签到")
    if uid.available:
        if uid.result not in api.data[session]["uid"]:
            return await app.send_message(sender, f"用户 {uid.result} 未绑定森空岛自动签到")
        api.data[session]["uid"].remove(uid.result)
        return await app.send_message(sender, f"用户 {uid.result} 解除森空岛自动签到成功")
    else:
        api.data.pop(session)
        return await app.send_message(sender, "解除森空岛自动签到成功")

@alcommand(alc)
@assign("查询")
@record("森空自动签到")
@exclusive
@accessable
async def check(app: Ariadne, sender: Sender, target: Target, uid: Match[str], _bot: RaianBotInterface):
    _record = _bot.data.cache.setdefault("sk_auto_sign_record", {})
    session = str(target.id)
    if session not in api.data:
        return await app.send_message(sender, "未绑定森空岛自动签到")
    if session not in _record:
        return await app.send_message(sender, "未进行签到，请等待")
    results = _record[session]
    if uid.available:
        if uid.result not in api.data[session]["uid"]:
            return await app.send_message(sender, f"用户 {uid.result} 未绑定森空岛自动签到")
        if uid.result not in results:
            return await app.send_message(sender, f"还未给用户 {uid.result} 进行签到，请等待")
        await app.send_message(sender, results[uid.result]["text"])
        results.pop(uid.result)
        return app.send_message(sender, "查询完毕，已清除结果")
    for res in results.values():
        await app.send_message(sender, res["text"])
    _record.pop(session)
    return app.send_message(sender, "查询完毕，已清除结果")

@crontab("30 0 * * * 0")
@record("森空自动签到", False)
async def shed():
    for account, app in Ariadne.instances.items():
        interface = app.launch_manager.get_interface(RaianBotInterface).bind(account)
        friends = [str(f.id) for f in (await app.get_friend_list())]
        data = interface.data
        _record = data.cache.setdefault("sk_auto_sign_record", {})
        keys = list(api.data.keys())
        for session in keys:
            _record[session] = {}
            async for res in api.sign(session):
                _record[session][res['target']] = res
                if session in friends:
                    await app.send_friend_message(int(session), res["text"])
                if not res["status"]:
                    logger.logger.debug(res)
                await asyncio.sleep(1)

@listen(ApplicationShutdown)
async def _save():
    api.save()
    await asyncio.sleep(0.1)
@every(1, "hour")
async def save():
    api.save()
    await asyncio.sleep(0.1)
