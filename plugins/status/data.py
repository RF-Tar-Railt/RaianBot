from __future__ import annotations

import asyncio
import os
import platform
from datetime import datetime
from typing import TYPE_CHECKING

import psutil
from loguru import logger

if TYPE_CHECKING:
    from psutil._common import sdiskusage

CURRENT_TIMEZONE = datetime.now().astimezone().tzinfo


def get_cpu_count():
    return psutil.cpu_count()


async def get_cpu_status() -> float:
    """Get the CPU usage status."""
    psutil.cpu_percent()
    await asyncio.sleep(0.5)
    return psutil.cpu_percent()


async def per_cpu_status() -> list[float]:
    """Get the CPU usage status of each core."""
    psutil.cpu_percent(percpu=True)
    await asyncio.sleep(0.5)
    return psutil.cpu_percent(percpu=True)  # type: ignore


def get_memory_status():
    """Get the memory usage status."""
    return psutil.virtual_memory()


def get_swap_status():
    """Get the swap usage status."""
    return psutil.swap_memory()


def _get_disk_usage(path: str) -> sdiskusage | None:
    try:
        return psutil.disk_usage(path)
    except Exception as e:
        logger.warning(f"Could not get disk usage for {path}: {e!r}")


def get_disk_usage() -> dict[str, sdiskusage]:
    """Get the disk usage status."""
    disk_parts = psutil.disk_partitions()
    return {d.mountpoint: usage for d in disk_parts if (usage := _get_disk_usage(d.mountpoint))}


def get_uptime() -> datetime:
    """Get the uptime of the mechine."""
    return datetime.fromtimestamp(psutil.boot_time(), tz=CURRENT_TIMEZONE)


def get_python_version() -> str:
    return platform.python_version()


def get_system_version() -> str:
    if platform.uname().system == "Windows":
        return platform.platform()
    else:
        return f"{platform.platform()} {platform.version()}"


def get_pid() -> int:
    return os.getpid()
