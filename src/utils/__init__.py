"""
Utility functions for the ENG_Agent project.

This package provides configuration management and various utilities.
"""

# 核心配置导出
from .config import (
    DASHSCOPE_API_KEY,
    BASE_URL,
    MODEL_NAME,
    MILVUS_HOST,
    MILVUS_PORT,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_URL,
)

# 定义公开接口列表
__all__ = [
    'DASHSCOPE_API_KEY',
    'BASE_URL',
    'MODEL_NAME',
    'MILVUS_HOST',
    'MILVUS_PORT',
    'POSTGRES_HOST',
    'POSTGRES_PORT',
    'POSTGRES_URL',
]
