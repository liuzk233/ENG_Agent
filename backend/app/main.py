"""
FastAPI 主入口

VocabWeaver API 服务
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    API_TITLE,
    API_DESCRIPTION,
    API_VERSION,
    CORS_ORIGINS,
    DEBUG,
)

# 配置日志
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


# ============================================================
# 应用生命周期
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("VocabWeaver API 启动中...")
    logger.info(f"调试模式: {DEBUG}")

    # 预编译 LangGraph（可选，加速首次请求）
    try:
        from src.graph.graph import compile_graph
        app.state.compiled_graph = compile_graph()
        logger.info("LangGraph 编译完成")
    except Exception as e:
        logger.warning(f"LangGraph 预编译失败: {e}")
        app.state.compiled_graph = None

    yield

    # 关闭时
    logger.info("VocabWeaver API 关闭中...")


# ============================================================
# 创建 FastAPI 应用
# ============================================================

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 监控与日志中间件
from .middleware import MonitoringMiddleware, LoggingMiddleware
from .middleware.monitoring import get_metrics

app.add_middleware(LoggingMiddleware, log_level="DEBUG" if DEBUG else "INFO")
app.add_middleware(MonitoringMiddleware)


# ============================================================
# 注册路由
# ============================================================

from .api.routes import sessions, history
from .api import websocket

app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(history.router, prefix="/api", tags=["history"])
app.include_router(websocket.router, tags=["websocket"])


# ============================================================
# 健康检查
# ============================================================

@app.get("/health", tags=["health"])
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": API_VERSION,
    }


@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """性能指标端点"""
    return {
        "version": API_VERSION,
        "metrics": get_metrics(),
    }


# ============================================================
# 根路由
# ============================================================

@app.get("/", tags=["root"])
async def root():
    """根路由"""
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "docs": "/docs",
    }
