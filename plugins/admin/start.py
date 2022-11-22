from typing import List

from app import RaianBotInterface
from graia.ariadne import Ariadne
from graia.ariadne.event.lifecycle import AccountLaunch
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.model.relationship import Group
from graiax.shortcut.saya import listen
from loguru import logger


from ..config.admin import AdminConfig


@listen(AccountLaunch)
async def _report(app: Ariadne, interface: RaianBotInterface):
    data = interface.data
    config = interface.config
    admin: "AdminConfig" = interface.config.plugin.get(AdminConfig)
    group_list: List[Group] = await app.get_group_list()
    groups = len(group_list)
    await app.send_friend_message(
        config.admin.master_id,
        MessageChain(
            f"机器人成功启动。\n",
            f"当前共加入了 {groups} 个群 \n",
            f"当前共有 {len(data.users)} 人参与签到",
        ),
    )
    if not admin.check_group_in_start:
        return
    gp_list = {i.id for i in group_list}
    joined_set = {int(i) for i in data.groups}
    count = 0
    for gp in joined_set.copy():
        if gp not in gp_list:
            if data.exist(gp):
                prof = data.get_group(gp)
                if prof.additional.get("mute", 6) != 6:
                    continue
                data.remove_group(gp)
            joined_set.remove(gp)
            logger.debug(f"发现失效群组: {gp}")
    for gp in group_list:
        if not data.exist(gp.id):
            logger.debug(f"发现新增群组: {gp.name}")
            data.add_group(gp.id)
            joined_set.add(gp.id)
            count += 1
            logger.debug(f"{gp.name} 初始化配置完成")
    data.cache["all_joined_group"] = list(joined_set)
    await app.send_friend_message(
        config.admin.master_id, MessageChain(f"共完成 {count} 个群组的初始化配置")
    )
