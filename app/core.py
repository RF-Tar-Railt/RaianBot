import asyncio
import time
import traceback
import random
from creart import it
from typing import Optional, List
from loguru import logger
from pathlib import Path
from contextlib import ExitStack
from datetime import datetime

from graia.ariadne.event.mirai import (
    MemberLeaveEventQuit, MemberJoinEvent,
    BotLeaveEventKick, NewFriendRequestEvent,
    BotInvitedJoinGroupRequestEvent, BotJoinGroupEvent
)
from graia.ariadne.message.element import Image, At
from graia.ariadne.event.lifecycle import ApplicationLaunched, ApplicationShutdowned
from graia.ariadne.event.message import GroupMessage, FriendMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model import Group, Member, Friend
from graia.ariadne.connection.config import config as conn_cfg, HttpClientConfig, WebsocketClientConfig
from graia.broadcast import Broadcast
from graia.broadcast.utilles import Ctx
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.builtin.event import ExceptionThrowed
from graia.ariadne.app import Ariadne
from graia.saya import Saya
from graia.scheduler import GraiaScheduler
from graia.scheduler.timers import every_hours
from arclet.alconna import Alconna
from arclet.alconna.graia import AlconnaBehaviour

from utils.generate_img import create_image
from utils.exception_report import generate_reports
from app.control import require_function
from .data import BotDataManager
from .config import BotConfig
from .logger import set_output

BotInstance: Ctx['RaianMain'] = Ctx("raian_bot")


class RaianMain:
    broadcast: Broadcast
    app: Ariadne
    config: BotConfig
    data: BotDataManager
    saya: Saya
    exit: asyncio.Event

    __slots__ = ("broadcast", "app", "config", "data", "saya", "exit")

    def __init__(self, config: BotConfig, debug_log: bool = True):
        """
        配置机器人参数

        Args:
            config: 机器人配置,
            debug_log: 是否记录 debug 日志
        """
        self.exit = asyncio.Event()
        self.config = config
        self.data = BotDataManager(config)
        Alconna.config(headers=self.config.command_prefix)
        set_output('DEBUG' if debug_log else 'INFO')
        self.app = Ariadne(
            connection=conn_cfg(
                config.account,
                config.verify_key,
                HttpClientConfig(config.url),
                WebsocketClientConfig(config.url)
            ),
            # log_config=LogConfig('DEBUG' if debug_log else 'INFO')
        )
        self.broadcast = self.app.broadcast
        self.saya = it(Saya)
        it(AlconnaBehaviour)
        scheduler = it(GraiaScheduler)
        logger.success("------------------机器人初始化完毕--------------------")

        @self.broadcast.finale_dispatchers.append
        class BotDispatcher(BaseDispatcher):
            @staticmethod
            async def catch(interface: "DispatcherInterface"):  # noqa
                if interface.annotation is RaianMain:
                    return self
                if interface.annotation is BotConfig:
                    return self.config
                if interface.annotation is BotDataManager:
                    return self.data

        @scheduler.schedule(every_hours())
        async def save():
            self.data.save()
            await asyncio.sleep(0)

    @classmethod
    def current(cls):
        """获取当前上下文的 Bot"""
        return BotInstance.get()

    @property
    def context(self):
        return BotInstance

    def load_plugins(self, path: Optional[str] = None):
        """从插件存放的文件夹中统一导入插件"""
        plugin_path = Path(path or self.config.plugin_path)
        if not plugin_path.is_dir():
            logger.error("插件路径应该为一存在的文件夹")
            return
        with ExitStack() as stack:
            stack.enter_context(BotInstance.use(self))
            stack.enter_context(self.saya.module_context())
            for file in plugin_path.iterdir():
                if file.is_file():
                    name = file.name.split('.')[0]
                    if name in self.config.disabled_plugins:
                        continue
                else:
                    name = file.name
                if name.startswith("_"):
                    continue
                try:
                    self.saya.require(f"{plugin_path.name}.{name}")
                except BaseException as e:
                    logger.warning(
                        f"fail to load {plugin_path.name}.{name}, caused by "
                        f"{traceback.format_exception(BaseException, e, e.__traceback__, 1)[-1]}"
                    )
                    self.stop()
                    raise e
                    #exit()

    def init_announcement(self, title: Optional[str] = None):
        """配置公告功能"""
        title = title or "来自管理者的公告"

        @self.broadcast.receiver(FriendMessage)
        async def announcement(app: Ariadne, friend: Friend, message: MessageChain):
            msg = message.as_sendable()
            if friend.id != self.config.master_id or not msg.startswith('公告:'):
                return
            msg.replace('公告:', '')
            ft = time.time()
            group_list = await app.get_group_list()
            for group in group_list:
                try:
                    await app.send_group_message(group.id, MessageChain(f'{title}\n') + msg)
                except Exception as err:
                    await app.send_friend_message(friend, MessageChain(f"{group.id} 的公告发送失败\n{err}"))
                await asyncio.sleep(random.uniform(2, 3))
            tt = time.time()
            times = str(tt - ft)
            await app.send_friend_message(friend, MessageChain(f"群发已完成，耗时 {times} 秒"))

    def init_group_report(self):
        """配置群组相关功能"""

        @self.broadcast.receiver(GroupMessage, priority=7)  # 防止可能的入群事件异常
        async def _init_g(app: Ariadne, group: Group):
            if not self.data.exist(group.id):
                self.data.add_group(group.id)
                self.data.cache['all_joined_group'].append(group.id)
                return await app.send_friend_message(
                    self.config.master_id, MessageChain(f"{group.name} 初始配置化完成")
                )

        @self.broadcast.receiver(BotLeaveEventKick)
        async def get_kicked(app: Ariadne, event: BotLeaveEventKick):
            self.data.cache['all_joined_group'].remove(event.group.id)
            self.data.remove_group(event.group.id)
            self.data.cache['blacklist'].append(event.group.id)
            await app.send_friend_message(self.config.master_id, MessageChain(
                "收到被踢出群聊事件",
                f"\n群号：{event.group.id}",
                f"\n群名：{event.group.name}",
                f"\n已添加至黑名单"
            ))

    def init_start_report(self, init_for_new_group: bool = True):
        """配置机器人启动事件"""

        @self.broadcast.receiver(ApplicationLaunched)
        async def _report(app: Ariadne):
            group_list: List[Group] = await app.get_group_list()
            groups = len(group_list)
            await app.send_friend_message(self.config.master_id, MessageChain(
                f"机器人成功启动。\n",
                f"当前共加入了 {groups} 个群 \n",
                f"当前共有 {len(self.data.users)} 人参与签到",
            ))
            if not init_for_new_group:
                return
            gp_list = {i.id for i in group_list}
            joined_set = {int(i) for i in self.data.groups}
            count = 0
            for gp in joined_set.copy():
                if gp not in gp_list:
                    logger.debug(f"发现失效群组: {gp}")
                    joined_set.remove(gp)
                    if self.data.exist(gp):
                        self.data.remove_group(gp)
            for gp in group_list:
                if not self.data.exist(gp.id):
                    logger.debug(f"发现新增群组: {gp.name}")
                    self.data.add_group(gp.id)
                    joined_set.add(gp.id)
                    count += 1
                    logger.debug(f"{gp.name} 初始化配置完成")
            self.data.cache['all_joined_group'] = list(joined_set)
            await app.send_friend_message(self.config.master_id, MessageChain(f"共完成 {count} 个群组的初始化配置"))

    def init_stop_report(self):
        """配置机器人关闭事件"""

        @self.broadcast.receiver(ApplicationShutdowned)
        async def _report(app: Ariadne):
            print(1)
            await app.send_friend_message(self.config.master_id, MessageChain("机器人关闭中。。。"))

    def init_exception_report(self):
        """配置运行时异常报告功能"""

        @self.broadcast.receiver(ExceptionThrowed)
        async def _report(app: Ariadne, event: ExceptionThrowed):
            tb = generate_reports(event.exception)
            tb.insert(0, f"在处理 {event.event} 时出现如下问题:")
            bts = await create_image('\n'.join(tb))
            await app.send_friend_message(self.config.master_id, MessageChain(Image(data_bytes=bts)))

    def init_member_change_report(self, welcome: Optional[str] = None):
        """配置用户相关事件"""
        welcome = welcome or (
            "欢迎新人！进群了就别想跑哦~\n来个star吧球球惹QAQ\n",
            "项目地址：https://github.com/RF-Tar-Railt/RaianBot"
        )

        @self.data.record("member_leave")
        @self.broadcast.receiver(MemberLeaveEventQuit, decorators=[require_function("member_leave")])
        async def member_leave_tell(app: Ariadne, group: Group, member: Member):
            """用户离群提醒"""
            await app.send_group_message(
                group,
                MessageChain("可惜了！\n" + member.name + '(' + str(member.id) + ")退群了！")
            )

        @self.data.record('member_join')
        @self.broadcast.receiver(MemberJoinEvent, decorators=[require_function("member_join")])
        async def member_join_tell(app: Ariadne, group: Group, member: Member):
            """用户入群提醒"""
            await app.send_group_message(group, MessageChain(At(member.id), welcome))

    def init_mute_change_report(self):
        """配置禁言相关事件"""

        @self.data.record('member_mute')
        @self.broadcast.receiver("MemberMuteEvent", decorators=[require_function("member_mute")])
        async def member_mute_tell(
                app: Ariadne,
                group: Group,
                target: Member
        ):
            """用户被禁言提醒"""
            await app.send_group_message(
                group, MessageChain("哎呀，", At(target.id), " 没法说话了！")
            )

        @self.data.record('member_unmute')
        @self.broadcast.receiver("MemberUnmuteEvent", decorators=[require_function("member_unmute")])
        async def member_unmute_tell(
                app: Ariadne,
                group: Group,
                target: Member,
                operator: Member
        ):
            """用户被解除禁言提醒, 注意是手动解禁"""
            if operator is not None:
                await app.send_group_message(
                    group, MessageChain("太好了!\n", At(target.id), " 被", At(operator.id), " 解救了！")
                )

    def init_request_report(self):
        """配置好友或群组申请响应"""

        @self.broadcast.receiver(NewFriendRequestEvent)
        async def get_friend_accept(app: Ariadne, event: NewFriendRequestEvent):
            """
            收到好友申请
            """
            if str(event.supplicant) in self.data.users:
                await event.accept()
                await app.send_friend_message(self.config.master_id, MessageChain(
                    "收到添加好友事件",
                    f"\nQQ：{event.supplicant}",
                    f"\n昵称：{event.nickname}",
                    f"\n状态：已通过申请\n\n{event.message.upper()}"
                ))
            else:
                await event.reject("请先签到")
                await app.send_friend_message(self.config.master_id, MessageChain(
                    "收到添加好友事件",
                    f"\nQQ：{event.supplicant}",
                    f"\n昵称：{event.nickname}",
                    f"\n状态：已拒绝申请\n\n{event.message.upper()}"
                ))

        @self.broadcast.receiver(BotInvitedJoinGroupRequestEvent)
        async def bot_invite(app: Ariadne, event: BotInvitedJoinGroupRequestEvent):
            """
            被邀请入群
            """
            friend_list = await app.get_friend_list()
            if event.supplicant in map(lambda x: x.id, friend_list):
                await app.send_friend_message(self.config.master_id, MessageChain(
                    "收到邀请入群事件",
                    f"\n邀请者：{event.supplicant} | {event.nickname}",
                    f"\n群号：{event.source_group}",
                    f"\n群名：{event.group_name}"
                ))
                await event.accept(f"{'该群已在黑名单中, 请告知管理员使用群管功能解除黑名单' if event.source_group in self.data.cache['blacklist'] else ''}")
            else:
                await event.reject("请先加机器人好友")

        @self.broadcast.receiver(BotJoinGroupEvent)
        async def get_join_group(app: Ariadne, group: Group):
            """
            收到入群事件
            """
            member_count = len(await app.get_member_list(group))
            await app.send_friend_message(self.config.master_id, MessageChain(
                "收到加入群聊事件",
                f"\n群号：{group.id}",
                f"\n群名：{group.name}",
                f"\n群人数：{member_count}"
            ))
            await app.send_group_message(group.id, MessageChain(
                f"我是 {self.config.master_name} 的机器人 {(await app.get_bot_profile()).nickname}\n",
                f"如果有需要可以联系主人{self.config.master_name}({self.config.master_id})，\n",
                f"尝试发送 {self.config.command_prefix[0]}帮助 以查看功能列表\n",
                "项目地址：https://github.com/RF-Tar-Railt/RaianBot\n",
                "机器人交流群：122680593"
            ))

    def init_greet(self):
        @self.data.record("greet")
        @self.broadcast.receiver(GroupMessage, priority=7, decorators=[require_function("greet")])
        async def _init_g(app: Ariadne, group: Group, message: MessageChain, member: Member):
            """简单的问好"""
            msg = message.display
            now = datetime.now()
            if (
                msg.startswith("早上好") or msg.startswith("早安") or msg.startswith("中午好") or msg.startswith("下午好")
                or msg.startswith("晚上好")
            ):
                if 6 <= now.hour < 11:
                    reply = "\t早上好~"
                elif 11 <= now.hour < 13:
                    reply = "\t中午好~"
                elif 13 <= now.hour < 18:
                    reply = "\t下午好~"
                elif 18 <= now.hour < 24:
                    reply = "\t晚上好~"
                else:
                    reply = "\t时候不早了，睡觉吧"
                await app.send_group_message(group, MessageChain(At(member.id), reply))

            if msg.startswith("晚安"):
                # if str(member.id) in sign_info:
                #     sign_info[str(member.id)]['trust'] += 1 if sign_info[str(member.id)]['trust'] < 200 else 0
                #     sign_info[str(member.id)]['interactive'] += 1
                if 0 <= now.hour < 6:
                    reply = "\t时候不早了，睡觉吧~(￣o￣) . z Z"
                elif 20 < now.hour < 24:
                    reply = "\t快睡觉~(￣▽￣)"
                else:
                    reply = "\t喂，现在可不是休息的时候╰（‵□′）╯"
                await app.send_group_message(group, MessageChain(At(member.id), reply))

    def start(self):
        if self.exit.is_set():
            logger.warning("机器人已经关闭！")
            return
        self.app.launch_blocking()

    def stop(self):
        """机器人结束运行方法"""
        if not self.exit.is_set():
            self.app.stop()
            self.data.save()
            logger.debug("机器人数据保存完毕")
            logger.success("机器人关闭成功. 晚安")
            self.exit.set()

    async def running(self):
        """异步启动机器人"""
        self.start()
        self.stop()
        await self.exit.wait()

    def running_sync(self):
        """同步启动机器人"""
        try:
            self.start()
        finally:
            self.stop()


__all__ = ["RaianMain"]
