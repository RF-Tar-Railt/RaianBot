import asyncio
import time
import traceback
import random
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
from graia.ariadne.model import Group, MiraiSession, Member, Friend, AriadneStatus
from graia.saya.builtins.broadcast import BroadcastBehaviour
from graia.broadcast import Broadcast
from graia.broadcast.utilles import Ctx
from graia.broadcast.entities.dispatcher import BaseDispatcher
from graia.broadcast.interfaces.dispatcher import DispatcherInterface
from graia.broadcast.builtin.event import ExceptionThrowed
from graia.ariadne.app import Ariadne
from graia.scheduler.saya import GraiaSchedulerBehaviour
from graia.scheduler import GraiaScheduler
from graia.saya import Saya
from arclet.alconna.graia.saya import AlconnaBehaviour
from arclet.alconna import command_manager

from utils.generate_img import create_image
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

    def __init__(
            self,
            config: BotConfig,
            *,
            loop: Optional[asyncio.AbstractEventLoop] = None,
            debug_log: bool = True
    ):
        """
        配置机器人参数

        Args:
            config: 机器人配置,
            loop: 事件循环
            debug_log: 是否记录 debug 日志
        """
        loop = loop or asyncio.get_event_loop()
        self.exit = asyncio.Event()
        self.config = config
        self.data = BotDataManager(config)
        self.broadcast = Broadcast(loop=loop)
        self.app = Ariadne(
            loop=loop,
            broadcast=self.broadcast,
            connect_info=MiraiSession(
                host=config.url,
                verify_key=config.verify_key,
                account=config.account,
            )
        )
        self.saya = self.app.create(Saya)
        self.saya.install_behaviours(
            BroadcastBehaviour(broadcast=self.broadcast),
            GraiaSchedulerBehaviour(GraiaScheduler(loop, self.broadcast)),
            AlconnaBehaviour(broadcast=self.broadcast, manager=command_manager)
        )
        set_output('DEBUG' if debug_log else 'INFO')
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

    @classmethod
    def current(cls):
        """获取当前上下文的 Bot"""
        return BotInstance.get()

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
                self.saya.require(f"{plugin_path.name}.{name}")

    def init_announcement(self, title: Optional[str] = None):
        """配置公告功能"""

        @self.broadcast.receiver(FriendMessage)
        async def announcement(app: Ariadne, friend: Friend, message: MessageChain):
            msg = message.asSendable()
            if friend.id != self.config.master_id or not msg.startswith('公告:'):
                return
            ft = time.time()
            group_list = await app.getGroupList()
            for group in group_list:
                try:
                    await app.sendGroupMessage(group.id, MessageChain.create(title))
                    await app.sendGroupMessage(group.id, msg)
                except Exception as err:
                    await app.sendFriendMessage(friend, MessageChain.create(f"{group.id} 的公告发送失败\n{err}"))
                await asyncio.sleep(random.uniform(2, 3))
            tt = time.time()
            times = str(tt - ft)
            await app.sendFriendMessage(friend, MessageChain.create(f"群发已完成，耗时 {times} 秒"))

    def init_group_report(self):
        """配置群组相关功能"""

        @self.broadcast.receiver(GroupMessage, priority=7)  # 防止可能的入群事件异常
        async def _init_g(app: Ariadne, group: Group):
            if not self.data.exist(group.id):
                self.data.add_group(group.id)
                self.data.cache['all_joined_group'].append(group.id)
                return await app.sendFriendMessage(
                    self.config.master_id, MessageChain.create(f"{group.name} 初始配置化完成")
                )

        @self.broadcast.receiver(BotLeaveEventKick)
        async def get_kicked(app: Ariadne, event: BotLeaveEventKick):
            self.data.cache['all_joined_group'].remove(event.group.id)
            self.data.remove_group(event.group.id)
            self.data.cache['blacklist'].append(event.group.id)
            await app.sendFriendMessage(self.config.master_id, MessageChain.create(
                "收到被踢出群聊事件",
                f"\n群号：{event.group.id}",
                f"\n群名：{event.group.name}",
                f"\n已添加至黑名单"
            ))

    def init_start_report(self, init_for_new_group: bool = True):
        """配置机器人启动事件"""

        @self.broadcast.receiver(ApplicationLaunched)
        async def _report(app: Ariadne):
            group_list: List[Group] = await app.getGroupList()
            groups = len(group_list)
            await app.sendFriendMessage(self.config.master_id, MessageChain.create(
                f"机器人成功启动。\n",
                f"当前共加入了 {groups} 个群 \n",
                f"当前共有 {len(self.data.users)} 人参与签到",
            ))
            if not init_for_new_group:
                return
            joined_set = {i for i in self.data.cache['all_joined_group']}
            count = 0
            for gp in group_list:
                if not self.data.exist(gp.id):
                    logger.debug(f"发现新增群组: {gp.name}")
                    self.data.add_group(gp.id)
                    joined_set.add(gp.id)
                    count += 1
                    logger.debug(f"{gp.name} 初始化配置完成")
            self.data.cache['all_joined_group'] = list(joined_set)
            await app.sendFriendMessage(self.config.master_id, MessageChain.create(f"共完成 {count} 个群组的初始化配置"))

    def init_stop_report(self):
        """配置机器人关闭事件"""

        @self.broadcast.receiver(ApplicationShutdowned)
        async def _report(app: Ariadne):
            await app.sendFriendMessage(self.config.master_id, MessageChain.create("机器人关闭中。。。"))

    def init_exception_report(self, level: int = 3):
        """配置运行时异常报告功能"""

        @self.broadcast.receiver(ExceptionThrowed)
        async def _report(app: Ariadne, event: ExceptionThrowed):
            exc = event.exception
            tb = traceback.format_exception(exc.__class__, exc, exc.__traceback__, limit=level)
            tb.insert(0, f"在处理 {event.event} 时出现如下问题:")
            bts = await create_image('\n'.join(tb), cut=120)
            await app.sendFriendMessage(self.config.master_id, MessageChain.create(Image(data_bytes=bts)))

    def init_member_change_report(self, welcome: Optional[str] = None):
        """配置用户相关事件"""
        welcome = welcome or "欢迎新人！进群了就别想跑哦~"

        @self.broadcast.receiver(MemberLeaveEventQuit)
        async def member_leave_tell(app: Ariadne, group: Group, member: Member):
            await app.sendGroupMessage(group, MessageChain.create(
                "可惜了！\n" + member.name + '(' + str(member.id) + ")退群了！"))

        @self.broadcast.receiver(MemberJoinEvent)
        async def member_join_tell(app: Ariadne, group: Group, member: Member):
            if group.id not in self.data.cache['blacklist']:
                await app.sendGroupMessage(group, MessageChain.create(At(member.id), welcome))

    def init_mute_change_report(self):
        """配置禁言相关事件"""

        @self.broadcast.receiver("MemberMuteEvent")
        async def member_mute_tell(
                app: Ariadne,
                group: Group, target_member: Member = 'target'
        ):
            await app.sendGroupMessage(
                group, MessageChain.create("哎呀，", At(target_member.id), " 没法说话了！")
            )

        @self.broadcast.receiver("MemberUnmuteEvent")
        async def member_unmute_tell(
                app: Ariadne,
                group: Group,
                target_member: Member = 'target',
                operator_member: Member = 'operator'
        ):
            if operator_member is not None:
                await app.sendGroupMessage(
                    group, MessageChain.create(
                        "太好了!\n", At(target_member.id), " 被", At(operator_member.id), " 解救了！"
                    )
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
                await app.sendFriendMessage(self.config.master_id, MessageChain.create(
                    "收到添加好友事件",
                    f"\nQQ：{event.supplicant}",
                    f"\n昵称：{event.nickname}",
                    f"\n状态：已通过申请\n\n{event.message.upper()}"
                ))
            else:
                await event.reject("请先签到")
                await app.sendFriendMessage(self.config.master_id, MessageChain.create(
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
            friend_list = await app.getFriendList()
            if event.supplicant in map(lambda x: x.id, friend_list):
                await app.sendFriendMessage(self.config.master_id, MessageChain.create(
                    "收到邀请入群事件",
                    f"\n邀请者：{event.supplicant} | {event.nickname}",
                    f"\n群号：{event.sourceGroup}",
                    f"\n群名：{event.groupName}",
                    "\n该群未在黑名单中，已同意加入"
                ))
                await event.accept("")
            else:
                await event.reject("请先加机器人好友")

        @self.broadcast.receiver(BotJoinGroupEvent)
        async def get_join_group(app: Ariadne, group: Group):
            """
            收到入群事件
            """
            member_count = len(await app.getMemberList(group))
            await app.sendFriendMessage(self.config.master_id, MessageChain.create(
                "收到加入群聊事件",
                f"\n群号：{group.id}",
                f"\n群名：{group.name}",
                f"\n群人数：{member_count}"
            ))
            await app.sendGroupMessage(group.id, MessageChain.create(
                f"我是 {self.config.master_name}",
                f"的机器人 {(await app.getBotProfile()).nickname}\n",
                f"如果有需要可以联系主人QQ ”{self.config.master_id}“，\n",
                f"尝试发送 {self.config.command_prefix[0]}帮助 以查看功能列表"
            ))

    def init_greet(self):
        @self.broadcast.receiver(GroupMessage, priority=7)  # 防止可能的入群事件异常
        async def _init_g(app: Ariadne, group: Group, message: MessageChain, member: Member):
            msg = message.asDisplay()
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
                await app.sendGroupMessage(group, MessageChain.create(At(member.id), reply))

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
                await app.sendGroupMessage(group, MessageChain.create(At(member.id), reply))

    async def start(self):
        if self.exit.is_set():
            logger.warning("机器人已经关闭！")
            return
        await self.app.lifecycle()

    async def stop(self):
        """机器人结束运行方法"""
        if not self.exit.is_set():
            self.app.status = AriadneStatus.SHUTDOWN
            await self.app.stop()
            self.data.save()
            logger.debug("机器人数据保存完毕")
            logger.success("机器人关闭成功. 晚安")
            self.exit.set()

    async def running(self):
        """异步启动机器人"""
        await self.start()
        await self.stop()
        await self.exit.wait()

    async def restart(self):
        """该方法功能正常未知"""
        await self.stop()
        self.exit.clear()
        await self.start()

    def running_sync(self):
        """同步启动机器人"""
        loop = self.app.loop
        try:
            loop.run_until_complete(self.start())
        finally:
            loop.run_until_complete(self.stop())


__all__ = ["RaianMain"]
