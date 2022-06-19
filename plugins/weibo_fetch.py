from typing import Union
from datetime import datetime
from arclet.alconna import Args
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.saya.channel import Channel
from graia.saya.builtins.broadcast import ListenerSchema
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Forward, ForwardNode, Source, Image
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.model import Group, Friend, Member
from graia.ariadne.app import Ariadne
from graia.scheduler.saya.schema import SchedulerSchema
from graia.scheduler.timers import every_minute

from app import RaianMain
from modules.weibo import WeiboAPI, WeiboDynamic
from utils.control import require_function

bot = RaianMain.current()
channel = Channel.current()

weibo_fetch = Alconna(
    "{target}动态", Args["index", int, 0],
    headers=bot.config.command_prefix,
    help_text="从微博获取指定用户的动态 Usage: index 表示从最前动态排起的第几个动态; Example: .育碧动态;",
)

add_follower = Alconna(
    "增加微博关注", Args["target", str],
    headers=bot.config.command_prefix,
    help_text=f"增加一位微博动态关注对象 Example: {bot.config.command_prefix[0]}增加微博关注 育碧;"
)

remove_follower = Alconna(
    "解除微博关注", Args["target", str],
    headers=bot.config.command_prefix,
    help_text=f"删去一位微博动态关注对象 Example: {bot.config.command_prefix[0]}解除微博关注 育碧;"
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


@bot.data.record("获取微博动态")
@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=weibo_fetch, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage, FriendMessage], decorators=[require_function("获取微博动态")]))
async def fetch(
        app: Ariadne,
        target: Union[Member, Friend],
        sender: Union[Group, Friend],
        source: Source,
        result: AlconnaProperty
):
    arp = result.result
    if dynamic := await api.get_dynamic(arp.header['target'], index=arp.index):
        return await app.send_message(
            sender,
            MessageChain(Forward(*_handle_dynamic(
                dynamic, source.time, target.id, getattr(target, 'name', getattr(target, 'nickname', ""))
            )))
        )
    return await app.send_message(sender, MessageChain("获取失败啦"))


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=add_follower, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage]))
async def add(app: Ariadne, group: Group, source: Source, result: AlconnaProperty):
    if not bot.data.exist(group.id):
        return
    profile = bot.data.get_group(group.id)
    follower = await api.get_profile(result.result.target)
    if not (followers := profile.additional.get("weibo_followers")):
        followers = []
    if int(follower.id) in followers:
        return await app.send_group_message(group, MessageChain(f"该群已关注 {follower.name}！请不要重复关注"))
    followers.append(int(follower.id))
    profile.additional['weibo_followers'] = followers
    bot.data.update_group(profile)
    return await app.send_group_message(group, MessageChain(f"关注 {follower.name} 成功！"), quote=source.id)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=remove_follower, help_flag="reply")))
@channel.use(ListenerSchema([GroupMessage]))
async def add(app: Ariadne, group: Group, source: Source, result: AlconnaProperty):
    if not bot.data.exist(group.id):
        return
    profile = bot.data.get_group(group.id)
    follower = await api.get_profile(result.result.target, save=False)
    if not (followers := profile.additional.get("weibo_followers")):
        followers = []
    if int(follower.id) not in followers:
        return await app.send_group_message(group, MessageChain(f"该群未关注 {follower.name}！"))
    followers.remove(int(follower.id))
    profile.additional['weibo_followers'] = followers
    bot.data.update_group(profile)
    return await app.send_group_message(group, MessageChain(f"解除关注 {follower.name} 成功！"), quote=source.id)


@bot.data.record("微博动态自动获取")
@channel.use(SchedulerSchema(every_minute()))
async def update():
    dynamics = {}
    for gid in bot.data.groups:
        profile = bot.data.get_group(int(gid))
        if "微博动态自动获取" in profile.disabled:
            continue
        if not (followers := profile.additional.get("weibo_followers")):
            continue
        for uid in followers:
            if uid in dynamics:
                res = dynamics[uid]
            else:
                if not (res := await api.update(int(uid))):
                    continue
                dynamics[uid] = res
            now = datetime.now()
            if not (follower := await api.get_profile(int(uid), save=True)):
                continue
            await bot.app.send_group_message(profile.id, MessageChain(f"{follower.name} 有一条新动态！请查收!"))
            await bot.app.send_group_message(profile.id, MessageChain(
                Forward(*_handle_dynamic(res, now, bot.config.account, bot.config.bot_name))
            ))
    dynamics.clear()
