"""建表脚本：根据 ORM 模型在数据库中创建全部表。

用法: python -m app.init_db
SQLite 与 MariaDB 通用（通过 DATABASE_URL 切换）。
"""
from app.core.logger import setup_logging, get_logger
from app.db import Base, engine, db_session
# 必须导入 models 以触发注册
from app import models  # noqa: F401
from app.models import User
from app.core.auth import hash_password


def create_admin_user():
    """创建默认管理员账号。"""
    with db_session() as session:
        admin = session.query(User).filter(User.username == "admin").first()
        if admin is None:
            admin = User(
                username="admin",
                hashed_password=hash_password("admin123"),
                is_active=True,
                is_admin=True,
            )
            session.add(admin)
            session.commit()
            return True
        elif not admin.is_admin:
            admin.is_admin = True
            session.commit()
            return True
        return False


def main():
    setup_logging()
    log = get_logger(__name__)
    log.info("开始建表 @ %s", engine.url)
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import inspect
    tables = inspect(engine).get_table_names()
    log.info("建表完成，共 %d 张表: %s", len(tables), tables)

    # 创建管理员账号
    if create_admin_user():
        log.info("管理员账号创建成功: admin / admin123")
    else:
        log.info("管理员账号已存在")


if __name__ == "__main__":
    main()
