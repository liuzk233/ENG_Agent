"""
Milvus 知识库构建脚本

功能：
1. Markdown 文档切片（保留标题层级上下文）
2. 词汇软过滤（打标记，不删除切片）
3. DashScope Embedding 向量化
4. Milvus 灌库（含混合索引）
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from pymilvus import (
    connections, Collection, CollectionSchema, FieldSchema, DataType, utility
)

from src.utils.config import (
    DASHSCOPE_API_KEY, BASE_URL,
    MILVUS_HOST, MILVUS_PORT, MILVUS_COLLECTION_NAME,
    EMBEDDING_MODEL, EMBEDDING_DIM, EMBEDDING_BACKEND
)
from src.data_pipeline.parsers.extractor import load_syllabus_xls
from src.agents.reviewer import check_vocabulary
from .embedder import get_embedder

logger = logging.getLogger(__name__)


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class Chunk:
    """文本切片"""
    text: str
    metadata: dict = field(default_factory=dict)


# ============================================================
# Markdown 切片器
# ============================================================

def split_markdown(md_text: str, source: str = "") -> List[Chunk]:
    """
    按 Markdown 标题层级切片，保留层级上下文为 metadata

    例：一段位于 "# Ch1" > "## Section A" 下的文本，
    metadata 会包含 {"h1": "Ch1", "h2": "Section A"}
    """
    heading_re = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    positions = [
        (m.start(), len(m.group(1)), m.group(2).strip())
        for m in heading_re.finditer(md_text)
    ]

    if not positions:
        text = md_text.strip()
        return [Chunk(text=text, metadata={"source": source})] if text else []

    chunks = []
    context: dict = {}

    for i, (pos, level_num, title) in enumerate(positions):
        # 当前层级覆盖，更深层级清空
        context[f"h{level_num}"] = title
        for deeper in range(level_num + 1, 7):
            context.pop(f"h{deeper}", None)

        end = positions[i + 1][0] if i + 1 < len(positions) else len(md_text)
        body = md_text[pos:end].strip()
        if body:
            chunks.append(Chunk(text=body, metadata={"source": source, **context}))

    return chunks


def extract_metadata(file_path: str) -> dict:
    """从文件路径提取元数据：父目录名作为分类标签"""
    p = Path(file_path)
    return {
        "category": p.parent.name,
        "file_name": p.name,
        "genre": p.parent.name,  # genre 默认等于 category
    }


# ============================================================
# 知识库构建器
# ============================================================

class MilvusKnowledgeBaseBuilder:
    """
    Milvus 知识库构建器

    Features:
    - 词汇软过滤：保留所有切片，打上审查标记
    - 混合索引：HNSW 向量索引 + Trie 标量索引
    - 幂等重建：每次构建先删除旧 Collection
    """

    def __init__(
        self,
        milvus_host: str = None,
        milvus_port: int = None,
        collection_name: str = None,
        syllabus_path: str = None,
        embedding_model: str = None,
        embedding_dim: int = None,
        enable_pre_filter: bool = True,
    ):
        """
        初始化构建器

        Args:
            milvus_host: Milvus 服务地址
            milvus_port: Milvus 服务端口
            collection_name: Collection 名称
            syllabus_path: 大纲词汇表路径（用于软过滤）
            embedding_model: Embedding 模型名称
            embedding_dim: 向量维度
            enable_pre_filter: 是否启用词汇预过滤
        """
        self.milvus_host = milvus_host or MILVUS_HOST
        self.milvus_port = milvus_port or MILVUS_PORT
        self.collection_name = collection_name or MILVUS_COLLECTION_NAME
        self.embedding_model = embedding_model or EMBEDDING_MODEL
        self.embedding_dim = embedding_dim or EMBEDDING_DIM
        self.enable_pre_filter = enable_pre_filter

        # 加载大纲词汇表
        if syllabus_path and enable_pre_filter:
            self.syllabus_set = load_syllabus_xls(syllabus_path)
            logger.info(f"📚 已加载大纲词汇: {len(self.syllabus_set)} 词")
        else:
            self.syllabus_set = None

        # 初始化 Embedder（根据配置选择后端）
        # BGE-M3 需要较小的 batch_size 以节省显存
        self.embedder = get_embedder(batch_size=8)

    def build(self, input_dir: str | Path) -> int:
        """
        构建知识库

        Args:
            input_dir: Markdown 文件目录

        Returns:
            写入的向量数量
        """
        input_dir = Path(input_dir)

        # 1. 校验输入
        if not input_dir.is_dir():
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")

        md_files = list(input_dir.rglob("*.md"))
        if not md_files:
            raise ValueError(f"输入目录中未找到 .md 文件: {input_dir}")

        logger.info(f"📄 找到 {len(md_files)} 个 Markdown 文件")

        # 2. 切片
        all_chunks = self._chunk_documents(md_files)
        logger.info(f"✂️ 共生成 {len(all_chunks)} 个切片")

        # 3. 词汇软过滤
        if self.enable_pre_filter and self.syllabus_set:
            all_chunks = self._soft_filter_vocabulary(all_chunks)

        if not all_chunks:
            raise ValueError("切片结果为空，请检查输入文件")

        # 4. 向量化
        logger.info(f"🔄 正在向量化 (model={self.embedding_model}, dim={self.embedding_dim})...")
        texts = [c.text for c in all_chunks]
        embeddings = self.embedder.embed(texts)

        # 5. 写入 Milvus
        self._write_to_milvus(all_chunks, embeddings)

        logger.info(f"✅ 知识库构建完成！共 {len(all_chunks)} 条向量")
        return len(all_chunks)

    def _chunk_documents(self, md_files: List[Path]) -> List[Chunk]:
        """切分所有文档"""
        all_chunks = []
        for fp in md_files:
            text = fp.read_text(encoding="utf-8")
            file_meta = extract_metadata(str(fp))
            chunks = split_markdown(text, source=str(fp))
            for chunk in chunks:
                chunk.metadata.update(file_meta)
                # 计算词数
                chunk.metadata["word_count"] = len(chunk.text.split())
            all_chunks.extend(chunks)
        return all_chunks

    def _soft_filter_vocabulary(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        词汇软过滤：保留所有切片，打上审查标记

        不删除任何切片，仅在 metadata 中标记：
        - is_vocabulary_clean: bool
        - out_of_scope_words: list (如果不通过)
        """
        clean_count = 0

        for chunk in chunks:
            # 只对英文文本进行词汇检查
            # 简单判断：如果文本中英文字符占比超过 50%
            english_ratio = sum(c.isascii() and c.isalpha() for c in chunk.text) / max(len(chunk.text), 1)

            if english_ratio < 0.5:
                # 非英文为主的内容，默认通过
                chunk.metadata["is_vocabulary_clean"] = True
                chunk.metadata["out_of_scope_words"] = ""
                clean_count += 1
                continue

            # 执行词汇检查
            is_clean, feedback = check_vocabulary(
                text=chunk.text,
                syllabus_set=self.syllabus_set,
                target_words=[],
                llm_client=None  # 离线模式，不启用 LLM 兜底
            )

            chunk.metadata["is_vocabulary_clean"] = is_clean

            if is_clean:
                chunk.metadata["out_of_scope_words"] = ""
                clean_count += 1
            else:
                # 提取超纲词列表
                out_of_scope_words = self._extract_bad_words(feedback)
                chunk.metadata["out_of_scope_words"] = ",".join(out_of_scope_words)
                logger.warning(
                    f"⚠️ 切片含 {len(out_of_scope_words)} 个超纲词: {chunk.text[:50]}..."
                )

        logger.info(f"🔍 词汇审查完成: {clean_count}/{len(chunks)} 切片通过")
        return chunks

    def _extract_bad_words(self, feedback: str) -> List[str]:
        """从 feedback 中提取超纲词列表"""
        match = re.search(r'\[([^\]]+)\]', feedback)
        if match:
            return [w.strip() for w in match.group(1).split(',') if w.strip()]
        return []

    def _write_to_milvus(self, chunks: List[Chunk], embeddings: List[List[float]]):
        """写入 Milvus"""
        # 连接 Milvus
        connections.connect(
            alias="default",
            host=self.milvus_host,
            port=self.milvus_port
        )

        # 删除旧 Collection（幂等）
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
            logger.info(f"🗑️ 已删除旧 Collection: {self.collection_name}")

        # 创建新 Collection
        schema = self._create_schema()
        collection = Collection(name=self.collection_name, schema=schema)
        logger.info(f"📦 已创建 Collection: {self.collection_name}")

        # 创建索引
        self._create_indexes(collection)

        # 准备数据
        ids = []
        texts = []
        sources = []
        genres = []
        categories = []
        file_names = []
        h1_list = []
        h2_list = []
        word_counts = []
        is_clean_list = []
        out_of_scope_list = []

        for i, chunk in enumerate(chunks):
            # 生成唯一 ID
            unique_content = (
                f"{chunk.text[:100]}|"
                f"{chunk.metadata.get('source', '')}|"
                f"{chunk.metadata.get('h1', '')}|"
                f"{chunk.metadata.get('h2', '')}|{i}"
            )
            ids.append(hashlib.md5(unique_content.encode()).hexdigest())

            texts.append(chunk.text)
            sources.append(chunk.metadata.get("source", ""))
            genres.append(chunk.metadata.get("genre", ""))
            categories.append(chunk.metadata.get("category", ""))
            file_names.append(chunk.metadata.get("file_name", ""))
            h1_list.append(chunk.metadata.get("h1", ""))
            h2_list.append(chunk.metadata.get("h2", ""))
            word_counts.append(chunk.metadata.get("word_count", 0))
            is_clean_list.append(chunk.metadata.get("is_vocabulary_clean", True))
            # 截断超纲词列表到 500 字节（Schema 限制 512 字节，UTF-8 编码）
            out_words = chunk.metadata.get("out_of_scope_words", "")
            out_words_bytes = out_words.encode("utf-8")
            if len(out_words_bytes) > 500:
                out_words = out_words_bytes[:500].decode("utf-8", errors="ignore")
            out_of_scope_list.append(out_words)

        # 插入数据
        collection.insert([
            ids,
            texts,
            embeddings,
            sources,
            genres,
            categories,
            file_names,
            h1_list,
            h2_list,
            word_counts,
            is_clean_list,
            out_of_scope_list,
        ])

        # 刷新以确保数据持久化
        collection.flush()
        logger.info(f"💾 已写入 {len(chunks)} 条数据")

        # 加载 Collection 到内存
        collection.load()

    def _create_schema(self) -> CollectionSchema:
        """创建 Collection Schema"""
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),

            # 标量字段
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="genre", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="h1", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="h2", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="word_count", dtype=DataType.INT64),

            # 词汇审查字段（软过滤）
            FieldSchema(name="is_vocabulary_clean", dtype=DataType.BOOL),
            FieldSchema(name="out_of_scope_words", dtype=DataType.VARCHAR, max_length=512),
        ]

        return CollectionSchema(
            fields=fields,
            description="VocabWeaver RAG Knowledge Base",
            enable_dynamic_field=False
        )

    def _create_indexes(self, collection: Collection):
        """创建索引"""
        # 向量索引：HNSW
        vector_index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 256}
        }
        collection.create_index(field_name="embedding", index_params=vector_index_params)
        logger.info("📇 已创建向量索引: HNSW (COSINE)")

        # 标量索引：Trie（加速 VARCHAR 过滤）
        for field_name in ["genre", "category", "source"]:
            try:
                collection.create_index(
                    field_name=field_name,
                    index_params={"index_type": "Trie"}
                )
            except Exception:
                pass  # 某些字段可能不需要索引
        logger.info("📇 已创建标量索引: Trie")


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="构建 Milvus 知识库")
    parser.add_argument(
        "--input", "-i",
        type=str,
        default="data/processed/markdown",
        help="Markdown 文件目录"
    )
    parser.add_argument(
        "--syllabus", "-s",
        type=str,
        required=True,
        help="大纲词汇表路径 (.xls)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default=MILVUS_HOST,
        help="Milvus 服务地址"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=MILVUS_PORT,
        help="Milvus 服务端口"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=MILVUS_COLLECTION_NAME,
        help="Collection 名称"
    )

    args = parser.parse_args()

    builder = MilvusKnowledgeBaseBuilder(
        milvus_host=args.host,
        milvus_port=args.port,
        collection_name=args.collection,
        syllabus_path=args.syllabus,
    )

    builder.build(args.input)
