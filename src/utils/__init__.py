# src/utils/__init__.py
"""
Utility functions for the ENG_Agent project.

This package provides configuration management and RAG retrieval capabilities.

Example:
    >>> from utils import RAGRetriever
    >>> retriever = RAGRetriever()
    >>> results = retriever.retrieve("query")
"""

# 核心公开接口
from .config import DASHSCOPE_API_KEY, BASE_URL
from .rag_retriever import RAGRetriever

# 定义公开接口列表（用于 from utils import *）
__all__ = [
    'DASHSCOPE_API_KEY',
    'BASE_URL',
    'RAGRetriever',
]
