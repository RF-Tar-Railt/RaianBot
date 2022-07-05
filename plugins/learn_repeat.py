import ujson
import re
from datetime import datetime
from pathlib import Path

from arclet.alconna import Args, Empty, Option, AllParam, ArgParserTextFormatter, Arpamar
from arclet.alconna.graia import Alconna
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, At, Source, Plain, Face, ForwardNode, Forward
from graia.ariadne.model import Group, Member, BotMessage
from graia.ariadne.exception import UnknownTarget, UnknownError
from graia.ariadne.util.saya import listen, priority
from graia.broadcast.exceptions import PropagationCancelled
from contextlib import suppress

from app import RaianMain, record, command

bot = RaianMain.current()

repeat = Alconna(
    "学习回复",
    options=[
        Option("增加", Args["name", str]["content", AllParam], help_text="增加一条学习记录"),
        Option("删除", Args["name", [str, At]], help_text="删除一条学习记录, 若at用户则删除该用户的所有学习记录"),
        Option("查找", Args["target", str], help_text="查找是否有指定的学习记录"),
        Option("列出", Args["target", At, Empty], help_text="列出该群所有的学习记录, 若at用户则列出该用户的所有学习记录")
    ],
    headers=[''],
    help_text="让机器人记录指定内容并尝试回复 Example: 学习回复 增加 abcd xyz;",
    formatter_type=ArgParserTextFormatter
)

base_path = Path(f"{bot.config.cache_dir}/plugins/learn_repeat")
base_path.mkdir(parents=True, exist_ok=True)


@command(repeat, False)
async def fetch(
        app: Ariadne,
        target: Member,
        sender: Group,
        source: Source,
        result: Arpamar,
):
    if not result.options:
        return await app.send_message(sender, MessageChain(repeat.get_help()))
    this_file = base_path / f"record_{sender.id}.json"
    if result.find("列出"):
        if not this_file.exists():
            return await app.send_message(sender, MessageChain("该群未找到学习记录"))
        _target = result.query_with(At, "列出.target")
        with this_file.open("r+", encoding='utf-8') as f_obj:
            _data = ujson.load(f_obj)
        if not _data:
            return await app.send_message(sender, MessageChain("该群未找到学习记录"))
        keys = list(_data.keys())
        length = len(keys)
        for i in range(1 + (length-1) // 50):
            select = keys[i * 50: (i+1) * 50]
            forwards = []
            now = datetime.now()
            for key in select:
                _value = _data[key]
                if _target and _value['id'] != _target.target:
                    continue
                try:
                    name = (await app.getMember(sender, _value['id'])).name
                except (UnknownTarget, UnknownError):
                    name = str(_value['id'])
                forwards.append(
                    ForwardNode(
                        target=_value['id'],
                        name=name,
                        time=now,
                        message=MessageChain(f"{key}:\n") + MessageChain.from_persistent_string(_value['content'])
                    )
                )
            if not forwards:
                return await app.send_message(sender, MessageChain("呜, 找不到这个人的记录"))
            res: BotMessage = await app.send_message(sender, MessageChain(Forward(*forwards)))
            if res.messageId < 0:
                await app.send_message(sender, MessageChain("该群的记录中有敏感信息，无法列出"))
        return

    if result.find("查找"):
        if not this_file.exists():
            return await app.send_message(sender, MessageChain("该群未找到学习记录"))
        name = result.query("查找.target")
        with this_file.open("r+", encoding='utf-8') as f_obj:
            _data = ujson.load(f_obj)
        return await app.send_message(sender, MessageChain(f"查找{'成功' if name in _data else '失败'}！"))
    if result.find("删除"):
        if not this_file.exists():
            return await app.send_message(sender, MessageChain("该群未找到学习记录"))
        name = result.query("删除.name")
        with this_file.open("r+", encoding='utf-8') as f_obj:
            _data = ujson.load(f_obj)
        if isinstance(name, At):
            _record = None
            for key, value in _data.items():
                if value['id'] == name.target:
                    _record = _data.pop(key, None)
            if not _record:
                return await app.send_message(sender, MessageChain("呜, 找不到这个人的记录"), quote=source.id)
        else:
            if name not in _data:
                return await app.send_message(sender, MessageChain("呜, 找不到这条记录"), quote=source.id)
            del _data[name]
        with this_file.open("w+", encoding='utf-8') as f_obj:
            ujson.dump(_data, f_obj, ensure_ascii=False, indent=2)
        return await app.send_message(sender, MessageChain("删除记录成功了！"))

    if result.find("增加"):
        name, content = result.query("增加.name"), result.query("增加.content")
        if name in {"(.+?)", ".+?", ".*?", "(.*?)", ".+", ".*", "."}:
            return await app.send_message(sender, MessageChain("内容过于宽泛！"))
        name = name.replace("**", "*")
        _record = MessageChain(content)
        await _record.download_binary()
        _record = _record.include(Face, Image, Plain)
        if not _record:
            return await app.send_message(sender, MessageChain("喂, 没有内容啊~"))
        for elem in _record:
            if isinstance(elem, Image):
                elem.id = None
                elem.url = None
        if not this_file.exists():
            with this_file.open("w+", encoding='utf-8') as fo:
                ujson.dump({}, fo)
        if not this_file.exists():
            with this_file.open("w+", encoding='utf-8') as fo:
                ujson.dump({}, fo)
        with this_file.open("r+", encoding='utf-8') as f_obj:
            _data = ujson.load(f_obj)
        _data[name] = {"id": target.id, "content": _record.as_persistent_string()}
        with this_file.open("w+", encoding='utf-8') as fo:
            ujson.dump(_data, fo, ensure_ascii=False, indent=2)
        return await app.send_message(sender, MessageChain("我学会了！你现在可以来问我了！"), quote=source.id)


@record("repeat")
@listen(GroupMessage)
@priority(10)
async def handle(app: Ariadne, sender: Group, message: MessageChain):
    """依据记录回复对应内容"""
    this_file = base_path / f"record_{sender.id}.json"
    if not this_file.exists():
        return
    with this_file.open("r+", encoding='utf-8') as f_obj:
        _data = ujson.load(f_obj)
    msg = message.display
    with suppress(re.error):
        for key in _data.keys():
            if re.fullmatch(key, msg):
                content = _data[key]['content']
                res: BotMessage = await app.send_message(sender, MessageChain.from_persistent_string(content))
                if res.messageId < 0:
                    await app.send_message(sender, MessageChain("该条记录存在敏感信息，回复出错"))
                raise PropagationCancelled
    return
