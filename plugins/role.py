from typing import Tuple
from arclet.alconna import Args, Option, Empty, CommandMeta
from arclet.alconna.graia import Alconna, alcommand, assign, AtID, Match, AlconnaDispatcher
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Source, ForwardNode, Forward
from graia.ariadne.model import Group, Member

from app import record, RaianMain

role = Alconna(
    [''],
    "群员分组",
    Option("设置", Args["tag", str]["targets;S", AtID], help_text="设置分组并选择目标"),
    Option("增加", Args["tag", str]["targets;S", AtID], help_text="为分组增加目标"),
    Option("删除", Args["tag", str]["targets;S", AtID, Empty], help_text="删除指定分组或分组内的指定成员"),
    Option("呼叫", Args["tag", str]["content;O", str], help_text="At 指定分组下的群成员"),
    Option("列出", help_text="列出该群所有的分组"),
    meta=CommandMeta("为群成员设置特殊分组", usage="注意: 该命令不需要 “渊白” 开头")
)


@record('role')
@assign("$main")
@alcommand(role, private=False)
async def _r(app: Ariadne, sender: Group):
    return await app.send_message(sender, await AlconnaDispatcher.default_send_handler(role.get_help()))


@record('role')
@assign("列出")
@alcommand(role, private=False)
async def _r(app: Ariadne, target: Member, sender: Group, source: Source, bot: RaianMain):
    group = bot.data.get_group(sender.id)
    if not (roles := group.additional.get("roles")):
        roles = {}
    if not roles:
        return await app.send_group_message(sender, MessageChain("该群未设置有分组"))
    members = {i.id: i.name for i in await app.get_member_list(sender)}
    nodes = []
    notice = None
    for k, v in roles.copy().items():
        texts = []
        for id_ in v:
            if id_ not in members:
                roles[k].remove(id_)
                notice = MessageChain("发现无效成员, 已自动清理.")
            else:
                texts.append(f"{id_}: {members[id_]}")
        nodes.append(
            ForwardNode(target=target, time=source.time, message=MessageChain(f"【{k}】\n" + "\n".join(texts)))
        )
    await app.send_group_message(sender, MessageChain(Forward(*nodes)))
    if notice:
        await app.send_group_message(sender, notice)
    group.additional['roles'] = roles
    bot.data.update_group(group)


@assign("设置")
@record('role')
@alcommand(role, private=False)
async def _r(
        app: Ariadne, sender: Group, bot: RaianMain,
        tag: Match[str], targets: Match[Tuple[int, ...]]
):
    group = bot.data.get_group(sender.id)
    if not (roles := group.additional.get("roles")):
        roles = {}
    tag = tag.result
    targets = targets.result
    if not tag or not targets:
        return await app.send_group_message(sender, MessageChain("请输入正确参数"))
    roles[tag] = list(targets)
    await app.send_group_message(sender, MessageChain(f"分组 {tag} 设置成功"))
    group.additional['roles'] = roles
    bot.data.update_group(group)


@assign("增加")
@record('role')
@alcommand(role, private=False)
async def _r(
        app: Ariadne, sender: Group, bot: RaianMain,
        tag: Match[str], targets: Match[Tuple[int, ...]]
):
    group = bot.data.get_group(sender.id)
    if not (roles := group.additional.get("roles")):
        return await app.send_group_message(sender, MessageChain("请先设置新分组"))
    tag = tag.result
    targets = targets.result
    if not tag or not targets:
        return await app.send_group_message(sender, MessageChain("请输入正确参数"))
    if tag not in roles:
        return await app.send_group_message(sender, MessageChain(f"请先设置新分组: {tag}"))
    roles[tag] = list(set(roles[tag] + list(targets)))
    await app.send_group_message(sender, MessageChain(f"分组 {tag} 增加成员成功"))
    group.additional['roles'] = roles
    bot.data.update_group(group)


@record('role')
@assign("删除")
@alcommand(role, private=False)
async def _r(
        app: Ariadne, sender: Group, bot: RaianMain,
        tag: Match[str], targets: Match[Tuple[int, ...]]
):
    group = bot.data.get_group(sender.id)
    if not (roles := group.additional.get("roles")):
        roles = {}
    tag = tag.result
    if not tag:
        return await app.send_group_message(sender, MessageChain("请输入正确参数"))
    if tag not in roles:
        return await app.send_group_message(sender, MessageChain(f"分组 {tag} 不存在"))
    if not targets.available or not targets.result:
        del roles[tag]
        await app.send_group_message(sender, MessageChain(f"分组 {tag} 删除成功"))
    else:
        for i in filter(lambda x: x in roles[tag].copy(), targets.result):
            roles[tag].remove(i)
        await app.send_group_message(sender, MessageChain(f"分组 {tag} 清理成功"))
    group.additional['roles'] = roles
    bot.data.update_group(group)


@assign("呼叫")
@record('role')
@alcommand(role, private=False)
async def _r(
        app: Ariadne, sender: Group, bot: RaianMain,
        tag: Match[str], content: Match[str]
):
    group = bot.data.get_group(sender.id)
    if not (roles := group.additional.get("roles")):
        roles = {}
    tag = tag.result
    content = content.result if content.available else "📢"
    if not tag:
        return await app.send_group_message(sender, MessageChain("请输入正确参数"))
    if tag not in roles:
        return await app.send_group_message(sender, MessageChain(f"分组 {tag} 不存在"))
    ats = []
    members = [i.id for i in await app.get_member_list(sender)]
    notice = None
    for i in roles[tag].copy():
        if i not in members:
            roles[tag].remove(i)
            notice = MessageChain(f"{tag} 中发现无效成员, 已自动清理.")
        else:
            ats.append(At(i))
    if ats:
        await app.send_group_message(sender, MessageChain(content, *ats))
    else:
        await app.send_group_message(sender, MessageChain("呼叫失败"))
    if notice:
        await app.send_group_message(sender, notice)
    group.additional['roles'] = roles
    bot.data.update_group(group)
