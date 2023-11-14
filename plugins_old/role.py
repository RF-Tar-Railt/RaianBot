from typing import Tuple, NamedTuple, Dict, List, Optional
from arclet.alconna import Alconna, Args, Option, Empty, CommandMeta, MultiVar
from arclet.alconna.graia import alcommand, assign, Match
from graia.ariadne.app import Ariadne
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Source, ForwardNode, Forward
from graia.ariadne.model import Group, Member

from app import record, RaianBotInterface, meta_export, send_handler, accessable, exclusive


class roles(NamedTuple):
    data: Dict[str, List[int]]


meta_export(group_meta=[roles])

role = Alconna(
    [""],
    "群员分组",
    Option("设置", Args["tag", str]["targets", MultiVar(At, "+")], help_text="设置分组并选择目标"),
    Option("增加", Args["tag", str]["targets", MultiVar(At, "+")], help_text="为分组增加目标"),
    Option("删除", Args["tag", str]["targets", MultiVar(At, "+"), Empty], help_text="删除指定分组或分组内的指定成员"),
    Option("呼叫", Args["tag", str]["content;?", str], help_text="At 指定分组下的群成员"),
    Option("列出", help_text="列出该群所有的分组"),
    meta=CommandMeta("为群成员设置特殊分组", usage="注意: 该命令不需要 “渊白” 开头"),
)


@alcommand(role, private=False, comp_session={})
@record("role")
@assign("$main")
@exclusive
@accessable
async def _r_help(app: Ariadne, sender: Group):
    return await app.send_message(sender, await send_handler("help", role.get_help()))


@alcommand(role, private=False, comp_session={})
@record("role")
@assign("列出")
@exclusive
@accessable
async def _r_list(app: Ariadne, target: Member, sender: Group, source: Source, bot: RaianBotInterface):
    group = bot.data.get_group(sender.id)
    if not (_roles := group.get(roles)):
        return await app.send_group_message(sender, MessageChain("该群未设置有分组"))
    members = {i.id: i.name for i in await app.get_member_list(sender)}
    nodes = []
    notice = None
    data = _roles.data
    for k, v in data.copy().items():
        texts = []
        for id_ in v:
            if id_ not in members:
                data[k].remove(id_)
                notice = MessageChain("发现无效成员, 已自动清理.")
            else:
                texts.append(f"{id_}: {members[id_]}")
        nodes.append(ForwardNode(target=target, time=source.time, message=MessageChain(f"【{k}】\n" + "\n".join(texts))))
    await app.send_group_message(sender, MessageChain(Forward(*nodes)))
    if notice:
        await app.send_group_message(sender, notice)
        group.set(_roles)
        bot.data.update_group(group)


@alcommand(role, private=False, comp_session={})
@assign("设置")
@record("role")
@exclusive
@accessable
async def _r_set(app: Ariadne, sender: Group, bot: RaianBotInterface, tag: Match[str], targets: Match[Tuple[At, ...]]):
    group = bot.data.get_group(sender.id)
    _roles = group.get(roles, roles({}))
    _tag = tag.result
    _targets = [i.target for i in (targets.result or []) if i.target != app.account]
    if not _tag or not _targets:
        return await app.send_group_message(sender, MessageChain("请输入正确参数"))
    _roles.data[_tag] = _targets
    await app.send_group_message(sender, MessageChain(f"分组 {_tag} 设置成功"))
    group.set(_roles)
    bot.data.update_group(group)


@alcommand(role, private=False, comp_session={})
@assign("增加")
@record("role")
@exclusive
@accessable
async def _r_append(
    app: Ariadne, sender: Group, bot: RaianBotInterface, tag: Match[str], targets: Match[Tuple[At, ...]]
):
    group = bot.data.get_group(sender.id)
    if not (_roles := group.get(roles)):
        return await app.send_group_message(sender, MessageChain("请先设置新分组"))
    _tag = tag.result
    _targets = [i.target for i in (targets.result or []) if i.target != app.account]
    if not _tag or not _targets:
        return await app.send_group_message(sender, MessageChain("请输入正确参数"))
    if _tag not in _roles.data:
        return await app.send_group_message(sender, MessageChain(f"请先设置新分组: {_tag}"))
    _roles.data[_tag] = list(set(_roles.data[_tag] + _targets))
    await app.send_group_message(sender, MessageChain(f"分组 {_tag} 增加成员成功"))
    group.set(_roles)
    bot.data.update_group(group)


@alcommand(role, private=False, comp_session={})
@record("role")
@assign("删除")
@exclusive
@accessable
async def _r_remove(
    app: Ariadne, sender: Group, bot: RaianBotInterface, tag: Match[str], targets: Match[Optional[Tuple[At, ...]]]
):
    group = bot.data.get_group(sender.id)
    _roles = group.get(roles, roles({}))
    _tag = tag.result
    if not _tag:
        return await app.send_group_message(sender, MessageChain("请输入正确参数"))
    if _tag not in _roles.data:
        return await app.send_group_message(sender, MessageChain(f"分组 {_tag} 不存在"))
    if not targets.available or not targets.result:
        del _roles.data[_tag]
        await app.send_group_message(sender, MessageChain(f"分组 {_tag} 删除成功"))
    else:
        data = _roles.data[_tag].copy()
        for i in filter(lambda x: x.target in data, targets.result):
            _roles.data[_tag].remove(i.target)
        await app.send_group_message(sender, MessageChain(f"分组 {_tag} 清理成功"))
    group.set(_roles)
    bot.data.update_group(group)


@alcommand(role, private=False, comp_session={})
@assign("呼叫")
@record("role")
@exclusive
@accessable
async def _r_call(app: Ariadne, sender: Group, bot: RaianBotInterface, tag: Match[str], content: Match[str]):
    group = bot.data.get_group(sender.id)
    _roles = group.get(roles, roles({}))
    _tag = tag.result
    _content = content.result if content.available else "📢"
    if not tag.available or not _tag:
        return await app.send_group_message(sender, MessageChain("请输入正确参数"))
    if _tag not in _roles.data:
        return await app.send_group_message(sender, MessageChain(f"分组 {_tag} 不存在"))
    ats = []
    members = [i.id for i in await app.get_member_list(sender)]
    notice = None
    for i in _roles.data[_tag].copy():
        if i not in members:
            _roles.data[_tag].remove(i)
            notice = MessageChain(f"{tag} 中发现无效成员, 已自动清理.")
        else:
            ats.append(At(i))
    if ats:
        await app.send_group_message(sender, MessageChain(_content, *ats))
    else:
        await app.send_group_message(sender, MessageChain("呼叫失败"))
    if notice:
        await app.send_group_message(sender, notice)
        group.set(_roles)
        bot.data.update_group(group)
