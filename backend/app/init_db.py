"""建表脚本：根据 ORM 模型在数据库中创建全部表。

用法: python -m app.init_db
SQLite 与 MariaDB 通用（通过 DATABASE_URL 切换）。
"""
from app.core.logger import setup_logging, get_logger
from app.db import Base, engine
# 必须导入 models 以触发注册
from app import models  # noqa: F401


def main():
    setup_logging()
    log = get_logger(__name__)
    log.info("开始建表 @ %s", engine.url)
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import inspect
    tables = inspect(engine).get_table_names()
    log.info("建表完成，共 %d 张表: %s", len(tables), tables)


if __name__ == "__main__":
    main()
