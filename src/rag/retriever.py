"""
Milvus 向量检索器

支持混合检索（向量相似度 + 元数据过滤）和软过滤策略。
"""

import logging
import os
from typing import List, Optional

from pymilvus import connections, Collection

from src.utils.config import (
    DASHSCOPE_API_KEY, BASE_URL,
    MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME,
    EMBEDDING_MODEL, EMBEDDING_DIM
)

logger = logging.getLogger(__name__)


class MilvusRAGRetriever:
    """
    Milvus 向量检索器

    Features:
    - 混合检索：向量相似度 + 元数据过滤
    - 软过滤：通过 is_vocabulary_clean 字段控制
    - 语义门控：目标词少于 2 个时跳过检索
    """

    def __init__(
        self,
        collection_name: str = None,
        milvus_host: str = None,
        milvus_port: int = None,
        embedding_model: str = None,
        embedding_dim: int = None,
        top_k: int = 5,
        relevance_threshold: float = 0.75,
        strict_vocabulary: bool = True,
    ):
        """
        初始化 Milvus 检索器

        Args:
            collection_name: Collection 名称
            milvus_host: Milvus 服务地址
            milvus_port: Milvus 服务端口
            embedding_model: Embedding 模型名称
            embedding_dim: 向量维度
            top_k: 返回结果数量
            relevance_threshold: 相似度阈值
            strict_vocabulary: 是否只返回纯净语料（软过滤开关）
        """
        self.collection_name = collection_name or MILVUS_COLLECTION_NAME
        self.milvus_host = milvus_host or MILVUS_HOST
        self.milvus_port = milvus_port or MILVUS_PORT
        self.embedding_model = embedding_model or EMBEDDING_MODEL
        self.embedding_dim = embedding_dim or EMBEDDING_DIM
        self.top_k = top_k
        self.relevance_threshold = relevance_threshold
        self.strict_vocabulary = strict_vocabulary

        # 连接 Milvus
        self._connect()

        # 初始化 Embedder（根据配置选择后端）
        self._init_embedder()

        logger.info(
            f"✅ MilvusRAGRetriever 初始化: "
            f"collection={self.collection_name}, "
            f"host={self.milvus_host}:{self.milvus_port}, "
            f"strict_vocabulary={self.strict_vocabulary}"
        )

    def _init_embedder(self):
        """初始化 Embedder（支持 DashScope 或 BGE-M3 本地）"""
        backend = os.getenv("EMBEDDING_BACKEND", "dashscope")

        if backend == "bge-m3":
            from .embedder import BGEM3Embedding
            self.embedder = BGEM3Embedding(
                model_name="BAAI/bge-m3",
                device="cuda",
                batch_size=8,
            )
            self._use_local_embedder = True
            logger.info("🚀 使用 BGE-M3 本地向量化")
        else:
            from openai import OpenAI
            self.embedding_client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=BASE_URL)
            self._use_local_embedder = False
            logger.info("☁️ 使用 DashScope 云端向量化")

    def _connect(self):
        """连接 Milvus 并加载 Collection"""
        try:
            connections.connect(
                alias="default",
                host=self.milvus_host,
                port=self.milvus_port
            )
            self.collection = Collection(name=self.collection_name)
            self.collection.load()
            logger.info(f"📦 已加载 Collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"❌ 连接 Milvus 失败: {e}")
            raise

    def _embed_query(self, query: str) -> List[float]:
        """生成查询向量"""
        try:
            if self._use_local_embedder:
                # BGE-M3 本地向量化
                embeddings = self.embedder.embed([query])
                return embeddings[0]
            else:
                # DashScope 云端向量化
                response = self.embedding_client.embeddings.create(
                    model=self.embedding_model,
                    input=query,
                    dimensions=self.embedding_dim,
                )
                return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ 查询向量化失败: {e}")
            raise

    def _build_filter_expr(
        self,
        style: str = None,
        genre: str = None,
        min_word_count: int = None,
        max_word_count: int = None,
    ) -> Optional[str]:
        """
        构建 Milvus 过滤表达式

        Args:
            style: 风格过滤（对应 category 字段）
            genre: 体裁过滤
            min_word_count: 最小词数
            max_word_count: 最大词数

        Returns:
            过滤表达式字符串，无过滤条件时返回 None
        """
        conditions = []

        if style:
            conditions.append(f'category == "{style}"')
        if genre:
            conditions.append(f'genre == "{genre}"')
        if min_word_count is not None:
            conditions.append(f'word_count >= {min_word_count}')
        if max_word_count is not None:
            conditions.append(f'word_count <= {max_word_count}')

        # 软过滤：默认只返回纯净语料
        if self.strict_vocabulary:
            conditions.append("is_vocabulary_clean == true")

        return " && ".join(conditions) if conditions else None

    def retrieve(
        self,
        target_words: List[str],
        style: str = None,
        genre: str = None,
        min_word_count: int = None,
        max_word_count: int = None,
    ) -> List[str]:
        """
        执行混合检索

        Args:
            target_words: 目标词汇列表
            style: 风格过滤（对应 category 字段）
            genre: 体裁过滤
            min_word_count: 最小词数
            max_word_count: 最大词数

        Returns:
            相关文本列表（已过滤相似度阈值）
        """
        # 构建查询
        query_text = " ".join(target_words)
        if style:
            query_text = f"{query_text} {style}"

        logger.info(f"🔍 查询: {query_text}")

        # 生成查询向量
        query_embedding = self._embed_query(query_text)

        # 构建过滤表达式
        filter_expr = self._build_filter_expr(
            style=style,
            genre=genre,
            min_word_count=min_word_count,
            max_word_count=max_word_count,
        )
        if filter_expr:
            logger.info(f"🎯 过滤条件: {filter_expr}")

        # 执行检索
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 64}  # HNSW 搜索参数
        }

        try:
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=self.top_k,
                expr=filter_expr,
                output_fields=["text", "source", "genre", "category", "is_vocabulary_clean", "out_of_scope_words"]
            )
        except Exception as e:
            logger.error(f"❌ 检索失败: {e}")
            return []

        # 解析结果并应用相似度阈值
        filtered_results = []
        for hits in results:
            for hit in hits:
                similarity = 1 - hit.distance  # Cosine distance -> similarity
                if similarity >= self.relevance_threshold:
                    filtered_results.append(hit.entity.get("text"))

        if not filtered_results:
            logger.warning(f"⚠️ 无结果满足相似度阈值 {self.relevance_threshold}")
        else:
            logger.info(f"✅ 检索到 {len(filtered_results)} 条结果 (阈值={self.relevance_threshold})")

        return filtered_results

    def should_retrieve(self, target_words: List[str]) -> bool:
        """
        语义门控：判断是否需要执行检索

        Criteria:
        - 至少 2 个目标词（多词上下文效果更好）

        Args:
            target_words: 目标词汇列表

        Returns:
            bool: True 表示需要检索
        """
        if len(target_words) < 2:
            logger.info(f"⚡ 语义门控: 跳过检索（只有 {len(target_words)} 个词）")
            return False
        return True
