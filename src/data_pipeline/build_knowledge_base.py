"""
知识库构建流水线：Markdown 标题语义切片 → DashScope Embedding → ChromaDB 灌库

无 LlamaIndex 依赖，切片/向量化/存储全部轻量化自建。
跨系统兼容：使用 pathlib 处理路径，配置集中管理。
"""

import hashlib
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
from openai import OpenAI

from src.utils.config import DASHSCOPE_API_KEY, BASE_URL

logger = logging.getLogger(__name__)

# ============================================================
# 跨系统路径配置
# ============================================================

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent

# 数据目录配置（相对于项目根目录）
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed" / "markdown"
VECTOR_STORE_DIR = DATA_DIR / "vector_store" / "chromadb"


# ============================================================
# Markdown 语义切片器
# ============================================================

@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


def split_markdown(md_text: str, source: str = "") -> list[Chunk]:
    """
    按 Markdown 标题层级切片，保留层级上下文为 metadata。

    例：一段位于 "# Ch1" > "## Section A" 下的文本，
    metadata 会包含 {"h1": "Ch1", "h2": "Section A"}。
    """
    # 修复：raw string 中的 \s 在 Python 中是匹配空白字符，不需要转义
    heading_re = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    positions = [
        (m.start(), len(m.group(1)), m.group(2).strip())
        for m in heading_re.finditer(md_text)
    ]

    if not positions:
        text = md_text.strip()
        return [Chunk(text=text, metadata={"source": source})] if text else []

    chunks = []
    context: dict[str, str] = {}

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


# ============================================================
# DashScope Embedding（基于 OpenAI 兼容接口）
# ============================================================

class DashScopeEmbedding:
    """DashScope 文本向量化，自动分批处理"""

    # DashScope OpenAI 兼容模式单次 embedding 上限（实际限制为 10）
    BATCH_SIZE = 10

    def __init__(self, model: str = "text-embedding-v3", dimensions: int = 1024):
        self.client = OpenAI(api_key=DASHSCOPE_API_KEY, base_url=BASE_URL)
        self.model = model
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            resp = self.client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions,
            )
            # 按 index 排序确保顺序一致
            for item in sorted(resp.data, key=lambda x: x.index):
                all_embeddings.append(item.embedding)
        return all_embeddings


# ============================================================
# 元数据提取
# ============================================================

def extract_metadata(file_path: str) -> dict:
    """从文件路径提取元数据：父目录名作为分类标签"""
    p = Path(file_path)
    return {
        "category": p.parent.name,
        "file_name": p.name
    }


# ============================================================
# 知识库构建主流程
# ============================================================

def build_knowledge_base(
    input_dir: str | Path = PROCESSED_DIR,
    db_path: str | Path = VECTOR_STORE_DIR,
    collection_name: str = "vocabweaver_rag",
    embedding_model: str = "text-embedding-v3",
    embedding_dim: int = 1024,
):
    """
    构建向量知识库（幂等：每次重建先删旧 collection）。

    流程：读取 Markdown → 标题语义切片 → DashScope Embedding → ChromaDB 存储

    Args:
        input_dir: Markdown 文件目录（支持 str 或 Path）
        db_path: ChromaDB 存储路径（支持 str 或 Path）
        collection_name: Collection 名称
        embedding_model: Embedding 模型名称
        embedding_dim: Embedding 维度
    """
    # 转换为 Path 对象（跨系统路径处理）
    input_dir = Path(input_dir)
    db_path = Path(db_path)

    # --- 校验输入 ---
    if not input_dir.is_dir():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    md_files = list(input_dir.rglob("*.md"))
    if not md_files:
        raise ValueError(f"输入目录中未找到 .md 文件: {input_dir}")

    logger.info("找到 %d 个 Markdown 文件", len(md_files))

    # --- 切片 ---
    all_chunks: list[Chunk] = []
    for fp in md_files:
        text = fp.read_text(encoding="utf-8")
        file_meta = extract_metadata(str(fp))
        chunks = split_markdown(text, source=str(fp))
        for chunk in chunks:
            chunk.metadata.update(file_meta)
        all_chunks.extend(chunks)

    if not all_chunks:
        raise ValueError("切片结果为空，请检查 Markdown 文件内容")

    logger.info("共生成 %d 个切片", len(all_chunks))

    # --- 向量化 ---
    logger.info("正在向量化 (DashScope %s, dim=%d)...", embedding_model, embedding_dim)
    embedder = DashScopeEmbedding(model=embedding_model, dimensions=embedding_dim)
    texts = [c.text for c in all_chunks]
    embeddings = embedder.embed(texts)

    # --- 灌库（幂等：先删后建）---
    logger.info("正在写入 ChromaDB...")
    db_path.mkdir(parents=True, exist_ok=True)
    db = chromadb.PersistentClient(path=str(db_path))

    try:
        db.delete_collection(collection_name)
        logger.info("已删除旧 collection: %s", collection_name)
    except (ValueError, chromadb.errors.NotFoundError):
        pass  # collection 不存在，跳过

    collection = db.get_or_create_collection(
        collection_name,
        metadata={"hnsw:space": "cosine"}
    )

    # 使用文本 + metadata 生成唯一 ID，避免重复
    ids = []
    for i, chunk in enumerate(all_chunks):
        # 结合文本、文件路径、标题等信息生成更唯一的 ID
        unique_content = (
            f"{chunk.text[:100]}|"
            f"{chunk.metadata.get('source', '')}|"
            f"{chunk.metadata.get('h1', '')}|"
            f"{chunk.metadata.get('h2', '')}|{i}"
        )
        ids.append(hashlib.md5(unique_content.encode()).hexdigest())
    metadatas = [c.metadata for c in all_chunks]

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info("知识库构建完成！共 %d 条向量，存储于 %s", len(all_chunks), db_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    build_knowledge_base()
