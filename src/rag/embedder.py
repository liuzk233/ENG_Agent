"""
Embedding 模块：统一向量化解耦接口

支持两种后端：
1. DashScope API（云端）
2. BGE-M3 本地模型（GPU 加速）

通过环境变量 EMBEDDING_BACKEND 切换：dashscope | bge-m3
"""

import logging
from typing import List, Union

from openai import OpenAI

from src.utils.config import DASHSCOPE_API_KEY, BASE_URL, EMBEDDING_MODEL, EMBEDDING_DIM

logger = logging.getLogger(__name__)


# ============================================================
# BGE-M3 本地模型
# ============================================================

class BGEM3Embedding:
    """
    BGE-M3 本地向量化客户端

    Features:
    - GPU 加速（CUDA）
    - FP16 精度（节省显存）
    - 批量处理
    - 向量维度：1024

    依赖：
        pip install sentence-transformers
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cuda",
        batch_size: int = 32,
    ):
        """
        初始化 BGE-M3 模型

        Args:
            model_name: HuggingFace 模型名称
            device: 设备 (cuda / cpu)
            batch_size: 批处理大小
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "请安装 sentence-transformers: pip install sentence-transformers"
            )

        # 检测 CUDA 可用性
        try:
            import torch
            if not torch.cuda.is_available():
                device = "cpu"
                logger.warning("⚠️ CUDA 不可用，将使用 CPU（速度较慢）")
        except ImportError:
            device = "cpu"

        logger.info(f"🔄 正在加载 BGE-M3 模型: {model_name}")
        logger.info(f"   设备: {device}")

        self.model = SentenceTransformer(model_name, device=device, trust_remote_code=True)
        self.batch_size = batch_size
        self.dimensions = 1024  # BGE-M3 向量维度

        logger.info(f"✅ BGE-M3 模型加载完成，向量维度: {self.dimensions}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        批量向量化文本

        Args:
            texts: 文本列表

        Returns:
            向量列表（与输入顺序一致）
        """
        if not texts:
            return []

        logger.info(f"🔄 正在向量化 {len(texts)} 条文本 (BGE-M3 本地)")

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=True,
            convert_to_numpy=True,
        ).tolist()

        logger.info(f"✅ 向量化完成: 共 {len(embeddings)} 条向量")
        return embeddings

    def embed_single(self, text: str) -> List[float]:
        """单条文本向量化"""
        embeddings = self.embed([text])
        return embeddings[0] if embeddings else []


# ============================================================
# DashScope 云端 API
# ============================================================

class DashScopeEmbedding:
    """
    DashScope 文本向量化客户端

    使用 OpenAI 兼容接口，支持自动分批处理。
    """

    # DashScope OpenAI 兼容模式单次 embedding 上限
    BATCH_SIZE = 10

    def __init__(
        self,
        model: str = None,
        dimensions: int = None
    ):
        """
        初始化 Embedding 客户端

        Args:
            model: Embedding 模型名称（默认使用配置）
            dimensions: 向量维度（默认使用配置）
        """
        self.client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=BASE_URL)
        self.model = model or EMBEDDING_MODEL
        self.dimensions = dimensions or EMBEDDING_DIM
        logger.info(f"📊 DashScope Embedding 初始化: model={self.model}, dim={self.dimensions}")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        批量向量化文本

        Args:
            texts: 文本列表

        Returns:
            向量列表（与输入顺序一致）
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        total_batches = (len(texts) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        for i in range(0, len(texts), self.BATCH_SIZE):
            batch_num = i // self.BATCH_SIZE + 1
            batch = texts[i : i + self.BATCH_SIZE]

            logger.info(f"🔄 正在向量化批次 {batch_num}/{total_batches} ({len(batch)} 条)")

            try:
                resp = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions,
                )
                # 按 index 排序确保顺序一致
                for item in sorted(resp.data, key=lambda x: x.index):
                    all_embeddings.append(item.embedding)

            except Exception as e:
                logger.error(f"❌ 向量化失败 (批次 {batch_num}): {e}")
                raise

        logger.info(f"✅ 向量化完成: 共 {len(all_embeddings)} 条向量")
        return all_embeddings

    def embed_single(self, text: str) -> List[float]:
        """
        单条文本向量化

        Args:
            text: 输入文本

        Returns:
            向量（list of float）
        """
        embeddings = self.embed([text])
        return embeddings[0] if embeddings else []


# ============================================================
# 统一工厂函数
# ============================================================

def get_embedder(backend: str = None, **kwargs) -> Union[DashScopeEmbedding, BGEM3Embedding]:
    """
    获取 Embedder 实例

    Args:
        backend: 后端类型 (dashscope | bge-m3)
        **kwargs: 传递给具体 Embedder 的参数

    Returns:
        Embedder 实例
    """
    import os

    backend = backend or os.getenv("EMBEDDING_BACKEND", "dashscope")

    if backend == "bge-m3":
        logger.info("🚀 使用 BGE-M3 本地模型")
        return BGEM3Embedding(**kwargs)
    else:
        logger.info("☁️ 使用 DashScope 云端 API")
        return DashScopeEmbedding(**kwargs)
