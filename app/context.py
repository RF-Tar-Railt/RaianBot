from __future__ import annotations

from graia.broadcast.utilles import Ctx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import RaianBotService
    from .data import BotDataManager

BotInstance: Ctx["RaianBotService"] = Ctx("raian_bot")
DataInstance: Ctx["dict[int, BotDataManager]"] = Ctx("raian_data")
AccountDataInstance: Ctx["BotDataManager"] = Ctx("raian_data_account")

__all__ = ["BotInstance", "DataInstance", "AccountDataInstance"]
