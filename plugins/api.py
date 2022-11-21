from typing import List, Dict, Optional
from pydantic import BaseModel
from graiax.fastapi import route
from graia.saya import Saya
from creart import it
from app import UserProfile, GroupProfile, RaianBotService
from arclet.alconna import command_manager, CommandMeta
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
    return {"code": 200, "content": f"这里是{bot.config.bot_name}!"}


@route.route(["GET"], "/users", response_model=UsersResp)
async def get_users():
    ids = bot.data.users
    users = [bot.data.get_user(int(i)).dict() for i in ids]
    return JSONResponse(
        content={"count": len(ids), "users": users}, headers={"charset": "utf-8"}
    )


@route.route(["GET"], "/users/{uid}", response_model=UserFindResp)
@route.route(["GET"], "/user/get/{uid}", response_model=UserFindResp)
async def get_user(uid: int):
    res = bot.data.get_user(uid)
    return JSONResponse(
        content={"founded": bool(res), "user": res.dict()}, headers={"charset": "utf-8"}
    )


@route.route(["GET"], "/groups", response_model=GroupsResp)
async def get_groups():
    ids = bot.data.groups
    groups = [bot.data.get_group(int(i)).dict() for i in ids]
    return JSONResponse(
        content={"count": len(ids), "groups": groups}, headers={"charset": "utf-8"}
    )


@route.route(["GET"], "/groups/{gid}", response_model=GroupFindResp)
@route.route(["GET"], "/group/get/{gid}", response_model=GroupFindResp)
async def get_group(gid: int):
    res = bot.data.get_group(gid)
    return JSONResponse(
        content={"founded": bool(res), "group": res.dict()}, headers={"charset": "utf-8"}
    )


class HelpResp(BaseModel):
    count: int
    content: Dict[str, CommandMeta]


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


@route.route(["GET"], "/debug", response_model=DebugResp)
async def get_debug():
    return JSONResponse(
        content={
            "channels": len(it(Saya).channels),
            "groups": len(bot.data.groups),
            "users": len(bot.data.users),
            "disabled_plugins": bot.config.plugin.disabled,
        },
        headers={"charset": "utf-8"},
    )
