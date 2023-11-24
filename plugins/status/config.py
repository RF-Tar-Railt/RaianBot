from pydantic import Extra

from app.config import BasePluginConfig

CPU_TEMPLATE = r"""
CPU 核心数: {{ '%d' % cpu_count }}
CPU 占用率: {{ '%02d' % cpu_usage }}%
"""
"""Default CPU status template."""

# PER_CPU_TEMPLATE = (
#     "CPU:\n"
#     "{%- for core in per_cpu_usage %}\n"
#     "  core{{ loop.index }}: {{ '%02d' % core }}%\n"
#     "{%- endfor %}"
# )

MEMORY_TEMPLATE = r"内存占用: {{ '%02d' % memory_usage.percent }}%"
"""Default memory status template."""

SWAP_TEMPLATE = r"{% if swap_usage.total %}交换内存: {{ '%d' % swap_usage.percent }}%{% endif +%}"
"""Default swap status template."""

DISK_TEMPLATE = (
    "磁盘占用:\n"
    "{% for name, usage in disk_usage.items() %}\n"
    "  {{ name }}: {{ '%02d' % usage.percent }}%\n"
    "{% endfor %}"
)
"""Default disk status template."""

UPTIME_TEMPLATE = "机器运行时间: {{ uptime | relative_time | humanize_delta }}"
"""Default uptime status template."""

RUNTIME_TEMPLATE = "程序运行时间: {{ runtime | relative_time | humanize_delta }}"
"""Default runtime status template."""

PID_TEMPLATE = r"PID: {{ '%d' % pid }}"


PYTHON_VERSION_TEMPLATE = r"Python 版本: {{ python_version }}"

SYSTEM_VERSION_TEMPLATE = r"系统版本: {{ system_version }}"


class Config(BasePluginConfig, extra=Extra.ignore):
    truncate: bool = True
    """Whether to render the status template with used variables only."""

    template: str = "\n".join(
        (
            PID_TEMPLATE,
            PYTHON_VERSION_TEMPLATE,
            SYSTEM_VERSION_TEMPLATE,
            CPU_TEMPLATE,
            MEMORY_TEMPLATE,
            RUNTIME_TEMPLATE,
            UPTIME_TEMPLATE,
            SWAP_TEMPLATE,
            DISK_TEMPLATE,
        )
    )
    """Default server status template.

    Including:

    - CPU usage
    - Memory usage
    - Runtime
    - Uptime
    - Swap usage
    - Disk usage
    """


StatusConfig = Config
