from graia.broadcast.entities.event import Dispatchable
from graia.ariadne.model.relationship import Member
from graia.ariadne.dispatcher import MemberDispatcher, NoneDispatcher


class AccountMuted(Dispatchable):
    target: Member

    def __init__(self, target: Member):
        self.target = target

    dispatcher = MemberDispatcher


class AccountLimit(Dispatchable):
    code: int

    def __init__(self, code: int):
        self.code = code

    dispatcher = NoneDispatcher
