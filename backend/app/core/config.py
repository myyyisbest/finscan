"""全局配置 —— 基于 pydantic-settings，从环境变量/.env 读取。

数据库默认 SQLite（开发期跑通），生产切 MariaDB 仅需改 DATABASE_URL。
"""
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


# 后端根目录 (app/core/config.py -> app/core -> app -> backend)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# SQLite 数据文件放 backend/data/
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 应用 =====
    APP_NAME: str = "finscan"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # ===== 数据库 =====
    # SQLite 默认；切 MariaDB: mysql+pymysql://user:pwd@host:3306/finscan?charset=utf8mb4
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'finscan.db'}"

    # ===== JWT 鉴权 =====
    SECRET_KEY: str = "finscan-dev-secret-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 天

    # ===== 采集 =====
    COLLECT_SLEEP_MIN: float = 1.0   # 单次请求最小随机延时(秒)
    COLLECT_SLEEP_MAX: float = 3.0   # 单次请求最大随机延时(秒)
    COLLECT_RETRY: int = 3           # 失败重试次数
    COLLECT_TIMEOUT: int = 30        # 单请求超时(秒)
    # 全量初始化采集的股票范围: "all"=全A, "sample"=小样本(开发调试)
    COLLECT_SCOPE: str = "sample"

    # ===== AI (DeepSeek) =====
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # ===== 日志 =====
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
