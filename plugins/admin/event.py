from graia.broadcast.entities.event import Dispatchable
from graia.ariadne.model.relationship import Member
from graia.ariadne.dispatcher import MemberDispatcher, NoneDispatcher


class AccountMuted(Dispatchable):
    account: int
    target: Member

    def __init__(self, account: int, target: Member):
        self.account = account
        self.target = target

    dispatcher = MemberDispatcher


class AccountLimit(Dispatchable):
    account: int
    code: int

    def __init__(self, account: int, code: int):
        self.account = account
        self.code = code

    dispatcher = NoneDispatcher
