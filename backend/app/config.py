"""
Backend 配置管理

复用 src/utils/config.py 配置，添加 API 相关配置
"""

import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# 添加 src 到 path 以复用现有配置
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# 加载项目根目录下的 .env 文件
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# 复用现有配置
from utils.config import (
    DASHSCOPE_API_KEY,
    MODEL_NAME,
    BASE_URL,
    MILVUS_HOST,
    MILVUS_PORT,
    MILVUS_COLLECTION_NAME,
    VECTOR_STORE_TYPE,
    EMBEDDING_MODEL,
    EMBEDDING_DIM,
    EMBEDDING_BACKEND,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_DB,
    POSTGRES_URL,
)

# ============================================================
# FastAPI 配置
# ============================================================

API_TITLE = "VocabWeaver API"
API_DESCRIPTION = "多智能体英语文章生成系统"
API_VERSION = "2.0.0"

# CORS 配置
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

# 服务端口
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# 调试模式
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ============================================================
# 导出配置
# ============================================================

__all__ = [
    # API 配置
    "API_TITLE",
    "API_DESCRIPTION",
    "API_VERSION",
    "CORS_ORIGINS",
    "API_HOST",
    "API_PORT",
    "DEBUG",
    # 复用配置
    "DASHSCOPE_API_KEY",
    "MODEL_NAME",
    "BASE_URL",
    "MILVUS_HOST",
    "MILVUS_PORT",
    "MILVUS_COLLECTION_NAME",
    "VECTOR_STORE_TYPE",
    "EMBEDDING_MODEL",
    "EMBEDDING_DIM",
    "EMBEDDING_BACKEND",
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_URL",
]
