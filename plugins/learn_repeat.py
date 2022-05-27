import ujson
import re
from datetime import datetime
from pathlib import Path

from arclet.alconna import Args, Empty, Option, AllParam, ArgParserTextFormatter
from arclet.alconna.graia import Alconna, AlconnaDispatcher
from arclet.alconna.graia.dispatcher import AlconnaProperty
from arclet.alconna.graia.saya import AlconnaSchema
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, At, Source, Plain, Face, ForwardNode, Forward
from graia.ariadne.model import Group, Member
from graia.broadcast.exceptions import PropagationCancelled
from graia.saya.builtins.broadcast import ListenerSchema
from graia.saya.channel import Channel

from app import RaianMain

bot = RaianMain.current()
channel = Channel.current()

repeat = Alconna(
    "学习回复",
    options=[
        Option("增加", Args["name":str, "content":AllParam], help_text="增加一条学习记录"),
        Option("删除", Args["name":[str, At]], help_text="删除一条学习记录, 若at用户则删除该用户的所有学习记录"),
        Option("查找", Args["target":str], help_text="查找是否有指定的学习记录"),
        Option("列出", Args["target":At:Empty], help_text="列出该群所有的学习记录, 若at用户则列出该用户的所有学习记录")
    ],
    help_text="让机器人记录指定内容并尝试回复 Example: 莱安学习回复 增加 abcd xyz;",
    formatter=ArgParserTextFormatter()
)

base_path = Path(f"{bot.config.cache_dir}/plugins/learn_repeat")
base_path.mkdir(parents=True, exist_ok=True)


@channel.use(AlconnaSchema(AlconnaDispatcher(alconna=repeat, help_flag='reply')))
@channel.use(ListenerSchema([GroupMessage]))
async def fetch(
        app: Ariadne,
        target: Member,
        sender: Group,
        source: Source,
        result: AlconnaProperty
):
    arp = result.result
    this_file = base_path / f"record_{sender.id}.json"
    if arp.find("列出"):
        if not this_file.exists():
            return await app.sendMessage(sender, MessageChain.create("该群未找到学习记录"))
        _target = arp.query_with(At, "列出.target")
        with this_file.open("r+", encoding='utf-8') as f_obj:
            _data = ujson.load(f_obj)
        if not _data:
            return await app.sendMessage(sender, MessageChain.create("该群未找到学习记录"))
        keys = list(_data.keys())
        length = len(keys)
        for i in range(1 + (length-1) // 100):
            select = keys[i * 100: (i+1) * 100]
            forwards = []
            now = datetime.now()
            for key in select:
                _value = _data[key]
                if _target and _value['id'] != _target.target:
                    continue
                forwards.append(
                    ForwardNode(
                        target=_value['id'],
                        name=(await app.getMember(sender, _value['id'])).name,
                        time=now,
                        message=MessageChain.create(f"{key}:\n") + MessageChain.fromPersistentString(_value['content'])
                    )
                )
            await app.sendMessage(sender, MessageChain.create(Forward(*forwards)))
        return

    if arp.find("查找"):
        if not this_file.exists():
            return await app.sendMessage(sender, MessageChain.create("该群未找到学习记录"))
        name = arp.query("查找.target")
        with this_file.open("r+", encoding='utf-8') as f_obj:
            _data = ujson.load(f_obj)
        return await app.sendMessage(sender, MessageChain.create(f"查找{'成功' if name in _data else '失败'}！"))
    if arp.find("删除"):
        if not this_file.exists():
            return await app.sendMessage(sender, MessageChain.create("该群未找到学习记录"))
        name = arp.query("删除.name")
        with this_file.open("r+", encoding='utf-8') as f_obj:
            _data = ujson.load(f_obj)
        if isinstance(name, At):
            _record = None
            for key, value in _data.items():
                if value['id'] == name.target:
                    _record = _data.pop(key, None)
            if not _record:
                return await app.sendMessage(sender, MessageChain.create("呜, 找不到这个人的记录"), quote=source.id)
        else:
            if name not in _data:
                return await app.sendMessage(sender, MessageChain.create("呜, 找不到这条记录"), quote=source.id)
            del _data[name]
        with this_file.open("w+", encoding='utf-8') as f_obj:
            ujson.dump(_data, f_obj, ensure_ascii=False, indent=2)
        return await app.sendMessage(sender, MessageChain.create("删除记录成功了！"))

    if arp.find("增加"):
        name, content = arp.query("增加.name"), arp.query("增加.content")
        if name in {"(.+?)", ".+?", ".*?", "(.*?)", ".+", ".*", "."}:
            return await app.sendMessage(sender, MessageChain.create("内容过于宽泛！"))
        _record = MessageChain.create(content)
        await _record.download_binary()
        _record = _record.include(Face, Image, Plain)
        if not _record:
            return await app.sendMessage(sender, MessageChain.create("喂, 没有内容啊~"))
        for elem in _record:
            if isinstance(elem, Image):
                elem.id = None
                elem.url = None
        if not this_file.exists():
            with this_file.open("w+", encoding='utf-8') as fo:
                ujson.dump({}, fo)
        with this_file.open("r+", encoding='utf-8') as f_obj:
            _data = ujson.load(f_obj)
            f_obj.seek(0)
            # TODO: 放入数据库
            _data[name] = {"id": target.id, "content": _record.asPersistentString()}
            ujson.dump(_data, f_obj, ensure_ascii=False, indent=2)
        return await app.sendMessage(sender, MessageChain.create("我学会了！你现在可以来问我了！"), quote=source.id)


@channel.use(ListenerSchema([GroupMessage], priority=10))
async def handle(app: Ariadne, sender: Group, message: MessageChain):
    this_file = base_path / f"record_{sender.id}.json"
    if not this_file.exists():
        return
    with this_file.open("r+", encoding='utf-8') as f_obj:
        _data = ujson.load(f_obj)
    msg = message.asDisplay()
    for key in _data.keys():
        if re.fullmatch(key, msg):
            content = _data[key]['content']
            await app.sendMessage(sender, MessageChain.fromPersistentString(content))
            raise PropagationCancelled
    return
