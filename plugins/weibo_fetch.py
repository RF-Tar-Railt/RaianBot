from datetime import datetime
from arclet.alconna import Args, Option
from arclet.alconna.graia import Alconna, Match, command, match_path
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Forward, ForwardNode, Source, Image
from graia.ariadne.model import Friend
from graia.ariadne.app import Ariadne
from graia.ariadne.util.saya import decorate
from graia.scheduler.timers import every_minute

from app import RaianMain, Sender, Target, record, schedule
from modules.weibo import WeiboAPI, WeiboDynamic

bot = RaianMain.current()

weibo_fetch = Alconna(
    "微博", Args["user;O#微博用户名称", str],
    options=[
        Option(
            "动态", Args["index#从最前动态排起的第几个动态", int, 0],
            help_text="从微博获取指定用户的动态"
        ),
        Option("关注|增加关注", dest="follow", help_text="增加一位微博动态关注对象"),
        Option("取消关注|解除关注", dest="unfollow", help_text="解除一位微博动态关注对象"),
        Option("列出", dest="list", help_text="列出该群的微博动态关注对象")
    ],
    help_text="获取指定用户的微博资料 Example: $微博 育碧\n $微博 育碧 动态 1\n $微博 育碧 关注\n $微博 育碧 取消关注;"
)

api = WeiboAPI(f"{bot.config.cache_dir}/plugins/weibo_data.json")


def _handle_dynamic(
        data: WeiboDynamic,
        time: datetime,
        target: int,
        name: str
):
    text = MessageChain(data.text, *(Image(url=i) for i in data.img_urls))
    url = MessageChain(data.url)
    nodes = [text, url]
    if data.video_url:
        nodes.append(MessageChain(f"视频链接: {data.video_url}"))
    if data.retweet:
        nodes.append(MessageChain(Forward(*_handle_dynamic(data.retweet, time, target, name))))
    return [ForwardNode(target=target, name=name, time=time, message=i) for i in nodes]


@record("微博功能")
@command(weibo_fetch)
@decorate(match_path("$main"))
async def fetch(app: Ariadne, sender: Sender, user: Match[str]):
    if not user.available or not user.result:
        return await app.send_message(sender, MessageChain("不对劲。。。"))
    if prof := await api.get_profile(user.result, save=False):
        return await app.send_message(
            sender, MessageChain(
                Image(url=prof.avatar),
                f"用户名: {prof.name}\n",
                f"介绍: {prof.description}\n",
                f"动态数: {prof.statuses}\n",
                f"是否可见: {'是' if prof.visitable else '否'}"
            )
        )
    return await app.send_message(sender, MessageChain("获取失败啦"))


@record("微博功能")
@command(weibo_fetch)
@decorate(match_path("动态"))
async def fetch(
        app: Ariadne, target: Target, sender: Sender, source: Source,
        user: Match[str], index: Match[int]
):
    if dynamic := await api.get_dynamic(user.result, index=index.result):
        return await app.send_message(
            sender,
            MessageChain(Forward(*_handle_dynamic(
                dynamic, source.time, target.id, getattr(target, 'name', getattr(target, 'nickname', ""))
            )))
        )
    return await app.send_message(sender, MessageChain("获取失败啦"))


@record("微博功能")
@command(weibo_fetch)
@decorate(match_path("follow"))
async def fetch(app: Ariadne, sender: Sender, source: Source, user: Match[str]):
    if isinstance(sender, Friend):
        return
    if not bot.data.exist(sender.id):
        return
    prof = bot.data.get_group(sender.id)
    follower = await api.get_profile(user.result, save=True)
    if not (followers := prof.additional.get("weibo_followers")):
        followers = []
    if int(follower.id) in followers:
        return await app.send_message(sender, MessageChain(f"该群已关注 {follower.name}！请不要重复关注"))
    followers.append(int(follower.id))
    prof.additional['weibo_followers'] = followers
    bot.data.update_group(prof)
    return await app.send_message(sender, MessageChain(f"关注 {follower.name} 成功！"), quote=source.id)


@record("微博功能")
@command(weibo_fetch)
@decorate(match_path("unfollow"))
async def fetch(app: Ariadne, sender: Sender, source: Source, user: Match[str]):
    if isinstance(sender, Friend):
        return
    if not bot.data.exist(sender.id):
        return
    prof = bot.data.get_group(sender.id)
    follower = await api.get_profile(user.result, save=False)
    if not (followers := prof.additional.get("weibo_followers")):
        followers = []
    if int(follower.id) not in followers:
        return await app.send_message(sender, MessageChain(f"该群未关注 {follower.name}！"))
    followers.remove(int(follower.id))
    prof.additional['weibo_followers'] = followers
    bot.data.update_group(prof)
    return await app.send_message(sender, MessageChain(f"解除关注 {follower.name} 成功！"), quote=source.id)


@record("微博功能")
@command(weibo_fetch)
@decorate(match_path("list"))
async def fetch(app: Ariadne, target: Target, sender: Sender, source: Source):
    if isinstance(sender, Friend):
        return
    if not bot.data.exist(sender.id):
        return
    prof = bot.data.get_group(sender.id)
    if not (followers := prof.additional.get("weibo_followers")):
        followers = []
    nodes = []
    notice = None
    for uid in followers:
        if prof := await api.get_profile(uid, save=False):
            nodes.append(
                ForwardNode(
                    target=target,
                    time=source.time,
                    message=MessageChain(
                        Image(url=prof.avatar),
                        f"用户名: {prof.name}\n",
                        f"介绍: {prof.description}\n",
                        f"动态数: {prof.statuses}\n",
                        f"是否可见: {'是' if prof.visitable else '否'}"
                    )
                )
            )
        else:
            notice = MessageChain("获取信息发生错误，建议稍后再试")
    await app.send_group_message(sender, MessageChain(Forward(*nodes)))
    if notice:
        await app.send_group_message(sender, notice)


@record("微博动态自动获取", False)
@schedule(every_minute())
async def update():
    dynamics = {}
    for gid in bot.data.groups:
        prof = bot.data.get_group(int(gid))
        if "微博动态自动获取" in prof.disabled:
            continue
        if not (followers := prof.additional.get("weibo_followers")):
            continue
        for uid in followers:
            if uid in dynamics:
                res = dynamics[uid]
            elif res := await api.update(int(uid)):
                dynamics[uid] = res
            else:
                continue
            now = datetime.now()
            await bot.app.send_group_message(prof.id, MessageChain(f"{res.user.name} 有一条新动态！请查收!"))
            await bot.app.send_group_message(prof.id, MessageChain(
                Forward(*_handle_dynamic(res, now, bot.config.account, bot.config.bot_name))
            ))
    dynamics.clear()
