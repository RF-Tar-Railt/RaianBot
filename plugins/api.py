from typing import List, Dict, Optional
from graiax.fastapi import route
from graia.saya import Saya
from creart import it
from app import UserProfile, GroupProfile, RaianBotService, RaianBotInterface
from arclet.alconna import command_manager
from pydantic import BaseModel
from fastapi.responses import JSONResponse, PlainTextResponse
from dataclasses import asdict

bot = RaianBotService.current()


class GroupsResp(BaseModel):
    count: int
    groups: List[GroupProfile]


class UsersResp(BaseModel):
    count: int
    users: List[UserProfile]


class UserFindResp(BaseModel):
    founded: bool
    user: Optional[UserProfile]


class GroupFindResp(BaseModel):
    founded: bool
    group: Optional[GroupProfile]


@route.route(["GET"], "/")
async def root():
    return {"code": 200, "content": "这里是 Raian Bot API!"}


@route.route(["GET"], "/{account}/users", response_model=UsersResp)
async def get_users(account: int):
    interface = RaianBotInterface(bot, account)
    ids = interface.data.users
    users = [interface.data.get_user(int(i)).dict() for i in ids]
    return JSONResponse(
        content={"count": len(ids), "users": users}, headers={"charset": "utf-8"}
    )


@route.route(["GET"], "/{account}/users/{uid}", response_model=UserFindResp)
@route.route(["GET"], "/{account}/user/get/{uid}", response_model=UserFindResp)
async def get_user(account: int, uid: int):
    interface = RaianBotInterface(bot, account)
    res = interface.data.get_user(uid)
    return JSONResponse(
        content={"founded": bool(res), "user": res.dict()}, headers={"charset": "utf-8"}
    )


@route.route(["GET"], "/{account}/groups", response_model=GroupsResp)
async def get_groups(account: int):
    interface = RaianBotInterface(bot, account)
    ids = interface.data.groups
    groups = [interface.data.get_group(int(i)).dict() for i in ids]
    return JSONResponse(
        content={"count": len(ids), "groups": groups}, headers={"charset": "utf-8"}
    )


@route.route(["GET"], "/{account}/groups/{gid}", response_model=GroupFindResp)
@route.route(["GET"], "/{account}/group/get/{gid}", response_model=GroupFindResp)
async def get_group(account: int, gid: int):
    interface = RaianBotInterface(bot, account)
    res = interface.data.get_group(gid)
    return JSONResponse(
        content={"founded": bool(res), "group": res.dict()}, headers={"charset": "utf-8"}
    )


class HelpResp(BaseModel):
    count: int
    content: Dict[str, Dict]


@route.route(["GET"], "/help")
async def get_help():
    return PlainTextResponse(
        command_manager.all_command_help(), headers={"charset": "utf-8"}
    )


@route.route(["GET"], "/cmds", response_model=HelpResp)
async def get_cmds():
    cmds = list(command_manager.get_commands())
    return JSONResponse(
        content={"count": len(cmds), "content": {cmd.path: asdict(cmd.meta) for cmd in cmds}},
        headers={"charset": "utf-8"},
    )


class DebugResp(BaseModel):
    channels: int
    groups: int
    users: int
    disabled_plugins: List[str]


@route.route(["GET"], "/{account}/debug", response_model=DebugResp)
async def get_debug(account: int):
    interface = RaianBotInterface(bot, account)
    return JSONResponse(
        content={
            "channels": len(it(Saya).channels),
            "groups": len(interface.data.groups),
            "users": len(interface.data.users),
            "uninstalled_plugins": bot.config.plugin.disabled,
            "disabled_plugins": interface.config.disabled,
        },
        headers={"charset": "utf-8"},
    )
