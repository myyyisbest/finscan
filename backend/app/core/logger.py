"""统一日志配置：控制台彩色输出 + 可选文件。"""
import logging
import sys
from .config import settings

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def setup_logging() -> None:
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FMT))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # 降低第三方库噪音
    for noisy in ("urllib3", "apscheduler", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
