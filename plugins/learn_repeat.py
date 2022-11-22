import ujson
import re
from datetime import datetime
from pathlib import Path
from typing import Union, Optional, List
from arclet.alconna import Args, Empty, Option, AllParam, Arpamar, CommandMeta
from arclet.alconna.graia import Alconna, alcommand, assign, Match
from graia.ariadne.app import Ariadne
from graia.ariadne.event.message import GroupMessage
from graia.ariadne.message.chain import MessageChain
from graia.ariadne.message.element import Image, At, Source, Plain, Face, ForwardNode, Forward
from graia.ariadne.model import Group, Member
from graia.ariadne.exception import UnknownTarget, UnknownError
from graiax.shortcut.saya import listen, priority
from graia.broadcast.exceptions import PropagationCancelled
from contextlib import suppress

from app import RaianBotService, record, send_handler

bot = RaianBotService.current()

repeat = Alconna(
    [""],
    "学习回复",
    Option("增加", Args["name", str]["content", AllParam], help_text="增加一条学习记录"),
    Option("修改", Args["name", str]["content", AllParam], help_text="修改一条已存在的学习记录"),
    Option("删除", Args["target", [str, At]], help_text="删除一条学习记录, 若at用户则删除该用户的所有学习记录"),
    Option("查找", Args["target", str], help_text="查找是否有指定的学习记录"),
    Option("列出", Args["target", At, Empty], help_text="列出该群所有的学习记录, 若at用户则列出该用户的所有学习记录"),
    meta=CommandMeta("让机器人记录指定内容并尝试回复", usage="注意: 该命令不需要 “渊白” 开头", example="学习回复 增加 abcd xyz"),
)

base_path = Path(f"{bot.config.cache_dir}/plugins/learn_repeat")
base_path.mkdir(parents=True, exist_ok=True)


@alcommand(repeat, private=False)
@assign("$main")
async def shelp(app: Ariadne, sender: Group):
    return await app.send_message(sender, await send_handler(repeat.get_help()))


@alcommand(repeat, private=False)
@assign("列出")
async def rlist(app: Ariadne, sender: Group, target: Match[Optional[At]]):
    this_file = base_path / f"record_{sender.id}.json"
    if not this_file.exists():
        return await app.send_message(sender, MessageChain("该群未找到任何学习记录"))
    _target = target.result
    with this_file.open("r+", encoding="utf-8") as f_obj:
        _data = ujson.load(f_obj)
    if not _data:
        return await app.send_message(sender, MessageChain("该群未找到相关学习记录"))
    keys = list(_data.keys())
    for i in range(1 + (len(keys) - 1) // 50):
        select = keys[i * 50: (i + 1) * 50]
        forwards = []
        now = datetime.now()
        for key in select:
            _value = _data[key]
            if _target and _value["id"] != _target.target:
                continue
            try:
                name = (await app.get_member(sender, _value["id"])).name
            except (UnknownTarget, UnknownError):
                name = str(_value["id"])
            content = _value["content"]
            if _value.get("json"):
                send = MessageChain.parse_obj(ujson.loads(content))
            else:
                send = MessageChain.from_persistent_string(content)
                _value["content"] = send.json()
                _value["json"] = True
                with this_file.open("w+", encoding="utf-8") as fo:
                    ujson.dump(_data, fo, ensure_ascii=False, indent=2)
            forwards.append(
                ForwardNode(target=_value["id"], name=name, time=now, message=MessageChain(f"{key}:\n") + send)
            )
        if not forwards:
            return await app.send_message(sender, MessageChain("呜, 找不到这个人的记录"))
        res = await app.send_message(sender, MessageChain(Forward(*forwards)))
        if res.id < 0:
            await app.send_message(sender, MessageChain("该群的记录中有敏感信息，无法列出"))
    return


@alcommand(repeat, private=False)
@assign("查找")
async def rfind(app: Ariadne, sender: Group, target: Match[str]):
    this_file = base_path / f"record_{sender.id}.json"
    if not this_file.exists():
        return await app.send_message(sender, MessageChain("该群未找到任何学习记录"))
    name = target.result
    with this_file.open("r+", encoding="utf-8") as f_obj:
        _data = ujson.load(f_obj)
    if name not in _data:
        return await app.send_message(sender, MessageChain("查找失败！"))
    content = _data[name]["content"]
    if _data[name].get("json"):
        send = MessageChain.parse_obj(ujson.loads(content))
    else:
        send = MessageChain.from_persistent_string(content)
        _data[name]["content"] = send.json()
        _data[name]["json"] = True
        with this_file.open("w+", encoding="utf-8") as fo:
            ujson.dump(_data, fo, ensure_ascii=False, indent=2)
    return await app.send_message(sender, MessageChain("查找成功！\n内容为:\n") + send)


@alcommand(repeat, private=False)
@assign("删除")
async def rremove(app: Ariadne, sender: Group, source: Source, target: Match[Union[str, At]]):
    this_file = base_path / f"record_{sender.id}.json"
    if not this_file.exists():
        return await app.send_message(sender, MessageChain("该群未找到学习记录"))
    name = target.result
    with this_file.open("r+", encoding="utf-8") as f_obj:
        _data = ujson.load(f_obj)
    if isinstance(name, At):
        _record = None
        for key, value in _data.copy().items():
            if value["id"] == name.target:
                _record = _data.pop(key, None)
        if not _record:
            return await app.send_message(sender, MessageChain("呜, 找不到这个人的记录"), quote=source.id)
    elif name in _data:
        del _data[name]
    else:
        return await app.send_message(sender, MessageChain("呜, 找不到这条记录"), quote=source.id)

    with this_file.open("w+", encoding="utf-8") as f_obj:
        ujson.dump(_data, f_obj, ensure_ascii=False, indent=2)
    return await app.send_message(sender, MessageChain("删除记录成功了！"))


@alcommand(repeat, private=False, send_error=True)
@assign("增加")
async def radd(app: Ariadne, target: Member, sender: Group, source: Source, name: Match[str], result: Arpamar):
    this_file = base_path / f"record_{sender.id}.json"
    content = result.query_with(List[str], "增加.content") or []
    if name.result in {"(.+?)", ".+?", ".*?", "(.*?)", ".+", ".*", "."}:
        return await app.send_message(sender, MessageChain("内容过于宽泛！"))
    _name = name.result.replace("**", "*")
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
        with this_file.open("w+", encoding="utf-8") as fo:
            ujson.dump({}, fo)
    with this_file.open("r+", encoding="utf-8") as f_obj:
        _data = ujson.load(f_obj)
    _data[_name] = {"id": target.id, "content": _record.json(), "json": True}
    with this_file.open("w+", encoding="utf-8") as fo:
        ujson.dump(_data, fo, ensure_ascii=False, indent=2)
    return await app.send_message(sender, MessageChain("我学会了！你现在可以来问我了！"), quote=source.id)


@alcommand(repeat, private=False, send_error=True)
@assign("修改")
async def redit(app: Ariadne, target: Member, sender: Group, source: Source, name: Match[str], result: Arpamar):
    this_file = base_path / f"record_{sender.id}.json"
    content = result.query_with(List[str], "增加.content") or []
    if name.result in {"(.+?)", ".+?", ".*?", "(.*?)", ".+", ".*", "."}:
        return await app.send_message(sender, MessageChain("内容过于宽泛！"))
    _name = name.result.replace("**", "*")
    if not this_file.exists():
        return await app.send_message(sender, MessageChain("该群未找到任何学习记录"))
    with this_file.open("r+", encoding="utf-8") as f_obj:
        _data = ujson.load(f_obj)
    if _name not in _data:
        return await app.send_message(sender, MessageChain("该群不存在该学习记录！"))
    _record = MessageChain(content)
    await _record.download_binary()
    _record = _record.include(Face, Image, Plain)
    if not _record:
        return await app.send_message(sender, MessageChain("喂, 没有内容啊~"))
    for elem in _record:
        if isinstance(elem, Image):
            elem.id = None
            elem.url = None
    _data[_name] = {"id": target.id, "content": _record.json(), "json": True}
    with this_file.open("w+", encoding="utf-8") as fo:
        ujson.dump(_data, fo, ensure_ascii=False, indent=2)
    return await app.send_message(sender, MessageChain("我学会了！你现在可以来问我了！"), quote=source.id)


@listen(GroupMessage)
@priority(10)
@record("repeat")
async def handle(app: Ariadne, sender: Group, message: MessageChain):
    """依据记录回复对应内容"""
    this_file = base_path / f"record_{sender.id}.json"
    if not this_file.exists():
        return
    with this_file.open("r+", encoding="utf-8") as f_obj:
        _data = ujson.load(f_obj)
    msg = message.display
    with suppress(re.error):
        for key in _data.keys():
            if re.fullmatch(key, msg):
                content = _data[key]["content"]
                if _data[key].get("json"):
                    send = MessageChain.parse_obj(ujson.loads(content))
                else:
                    send = MessageChain.from_persistent_string(content)
                    _data[key]["content"] = send.json()
                    _data[key]["json"] = True
                    with this_file.open("w+", encoding="utf-8") as fo:
                        ujson.dump(_data, fo, ensure_ascii=False, indent=2)
                res = await app.send_message(sender, send)
                if res.id < 0:
                    await app.send_message(sender, MessageChain("该条记录存在敏感信息，回复出错"))
                raise PropagationCancelled
    return
