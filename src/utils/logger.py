# src\utils\logger.py
import sys
import logging
from loguru import logger
from types import FrameType
from typing import cast

class InterceptHandler(logging.Handler):
    """
    拦截标准 logging 并将其转发到 Loguru
    """
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = cast(FrameType, frame.f_back)
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def setup_app_logging():
    """
    配置并接管所有日志输出
    """
    # 移除所有已存在的处理程序
    logging.root.handlers = [InterceptHandler()]
    logging.getLogger("uvicorn").handlers = []
    logging.getLogger("uvicorn.access").handlers = []

    # 配置 Loguru
    logger.remove()
    # 控制台输出
    logger.add(sys.stdout, colorize=True, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    # 文件输出
    logger.add("logs/fastapi_{time:YYYY-MM-DD}.log", rotation="1 day", retention="7 days")

# 导出 logger
__all__ = ["logger", "setup_app_logging"]