import sys

from loguru import logger

from excel_agent.core.config import settings


def setup_logging():
    """
    Cấu hình structured logging sử dụng loguru theo quy chuẩn AI Observability.
    """
    logger.remove()
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level> | "
        "<magenta>{extra}</magenta>"
    )
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=True,
    )
    logger.add(
        "logs/excel_agent.log",
        rotation="10 MB",
        retention="14 days",
        level="DEBUG",
        format="{time} | {level} | {name}:{function}:{line} | {message} | {extra}",
    )
    return logger


app_logger = setup_logging()
