from __future__ import annotations

from graia.broadcast.utilles import Ctx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import RaianBotService
    from .config import RaianConfig, BotConfig
    from .data import BotDataManager

BotInstance: Ctx["RaianBotService"] = Ctx("raian_bot")
MainConfigInstance: Ctx["RaianConfig"] = Ctx("raian_config_main")
BotConfigInstance: Ctx["BotConfig"] = Ctx("raian_config_bot")
DataInstance: Ctx["dict[int, BotDataManager]"] = Ctx("raian_data")
AccountDataInstance: Ctx["BotDataManager"] = Ctx("raian_data_account")

__all__ = ["BotInstance", "MainConfigInstance", "DataInstance", "AccountDataInstance", "BotConfigInstance"]
