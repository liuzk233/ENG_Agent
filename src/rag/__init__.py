"""
RAG 模块：向量检索与知识库构建

Components:
- embedder: 统一 Embedding 接口（支持 DashScope / BGE-M3）
- retriever: Milvus 向量检索器
- builder: 知识库构建脚本
"""

from .embedder import DashScopeEmbedding, BGEM3Embedding, get_embedder
from .retriever import MilvusRAGRetriever
from .builder import MilvusKnowledgeBaseBuilder

__all__ = [
    "DashScopeEmbedding",
    "BGEM3Embedding",
    "get_embedder",
    "MilvusRAGRetriever",
    "MilvusKnowledgeBaseBuilder",
]
