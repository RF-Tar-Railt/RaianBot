from arclet.alconna import Args, Option
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import At, Source, ForwardNode, Forward
from graia.ariadne.model import Group, Member
from graia.saya.builtins.broadcast import ListenerSchema
from graia.saya.channel import Channel

from app import RaianMain
from utils.control import require_function

bot = RaianMain.current()
channel = Channel.current()

role = Alconna(
    "群员分组",
    options=[
        Option("设置", Args["tag", str]["target;S", [At, int]], help_text="设置分组并选择目标"),
        Option("删除", Args["tag", str], help_text="删除指定分组"),
        Option("呼叫", Args["tag", str]["content;O", str], help_text="At 指定分组下的群成员"),
        Option("列出", help_text="列出该群所有的分组")
    ],
    help_text="为群成员设置特殊分组"
)


@bot.data.record("role")
@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=role, help_flag='reply')))
@channel.use(ListenerSchema([GroupMessage], decorators=[require_function("role")]))
async def _r(
        app: Ariadne,
        target: Member,
        sender: Group,
        source: Source,
        result: AlconnaProperty,
):
    arp = result.result
    if not arp.options:
        return await app.send_message(sender, MessageChain(role.get_help()))
    group = bot.data.get_group(sender.id)
    if not (roles := group.additional.get("roles")):
        roles = {}
    if arp.find("列出"):
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
    elif arp.find("设置"):
        tag = arp.query("设置.tag")
        targets = arp.query("设置.target")
        if not targets or not tag:
            return await app.send_group_message(sender, MessageChain("请输入正确参数"))
        roles[tag] = list(map(lambda x: x.target if isinstance(x, At) else x, targets))
        await app.send_group_message(sender, MessageChain(f"分组 {tag} 设置成功"))
    elif arp.find("删除"):
        tag = arp.query("删除.tag")
        if not tag:
            return await app.send_group_message(sender, MessageChain("请输入正确参数"))
        if tag not in roles:
            return await app.send_group_message(sender, MessageChain(f"分组 {tag} 不存在"))
        del roles[tag]
        await app.send_group_message(sender, MessageChain(f"分组 {tag} 删除成功"))
    elif arp.find("呼叫"):
        tag = arp.query("呼叫.tag")
        content = arp.query("呼叫.content", "")
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
            await app.send_group_message(sender, MessageChain(*ats, content))
        else:
            await app.send_group_message(sender, MessageChain("呼叫失败"))
        if notice:
            await app.send_group_message(sender, notice)
    group.additional['roles'] = roles
    bot.data.update_group(group)
