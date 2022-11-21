import os
import sys

from loguru import logger


info_format = (
    '<green>{time:YYYY-MM-DD HH:mm:ss.S}</green> | <level>{level: <8}</level> | '
    '<cyan>{name}</cyan> - <level>{message}</level>'
)
debug_format = (
    '<green>{time:YYYY-MM-DD HH:mm:ss.SSSS}</green> | <level>{level: <9}</level> | '
    '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level> '
)


def set_output(level='INFO'):
    log_format = debug_format if level == 'DEBUG' else info_format
    logger.remove()
    logger.add(
        "./logs/latest.log",
        format=log_format,
        level=level,
        enqueue=True,
        rotation="00:00",
        compression='zip',
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        colorize=False,
    )
    logger.add(
        sys.stderr, level=level,
        format=log_format, backtrace=True,
        diagnose=True, colorize=True
    )
