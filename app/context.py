from graia.broadcast.utilles import Ctx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import RaianBotService
    from .config import BotConfig
    from .data import BotDataManager

BotInstance: Ctx["RaianBotService"] = Ctx("raian_bot")
ConfigInstance: Ctx["BotConfig"] = Ctx("raian_config")
DataInstance: Ctx["BotDataManager"] = Ctx("raian_data")

__all__ = ["BotInstance", "ConfigInstance", "DataInstance"]
