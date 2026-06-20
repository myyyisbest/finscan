"""finscan FastAPI 应用入口。

启动: uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logger import setup_logging, get_logger
from app.core.exceptions import register_exception_handlers
from app.api import v1_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    log = get_logger(__name__)
    log.info("%s 启动 (debug=%s, db=%s)", settings.APP_NAME, settings.DEBUG, settings.DATABASE_URL)
    # 调度器在批次1.5接入
    yield
    log.info("%s 关闭", settings.APP_NAME)


app = FastAPI(
    title="finscan API",
    description="上市公司财报智能分析与风险排雷系统",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS（开发期允许前端 Vite 直连）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(v1_router)


@app.get("/")
def health():
    return {"app": settings.APP_NAME, "status": "running", "version": "0.1.0"}


@app.get(f"{settings.API_PREFIX}/ping")
def ping():
    return {"code": 0, "message": "pong"}
