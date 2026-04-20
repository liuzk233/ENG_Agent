"""
Milvus + BGE-M3 集成测试脚本

测试流程：
1. Milvus 连接测试
2. BGE-M3 模型加载测试
3. 向量写入测试
4. 向量检索测试
"""

import os
import sys

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 设置环境变量（测试时使用）
os.environ["DASHSCOPE_API_KEY"] = "test_key_for_bge_m3_test"  # 占位符，BGE-M3 不需要
os.environ["EMBEDDING_BACKEND"] = "bge-m3"
os.environ["MILVUS_HOST"] = "localhost"
os.environ["MILVUS_PORT"] = "19530"
os.environ["MILVUS_COLLECTION_NAME"] = "test_bge_m3"

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_milvus_connection():
    """测试 Milvus 连接"""
    print("\n" + "=" * 50)
    print("1. 测试 Milvus 连接")
    print("=" * 50)

    try:
        from pymilvus import connections, utility

        connections.connect(
            alias="default",
            host="localhost",
            port="19530"
        )
        print("   ✅ 连接成功")

        # 列出现有 collections
        collections = utility.list_collections()
        print(f"   现有 Collections: {collections if collections else '无'}")

        return True
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        print("   请确保 Milvus 容器正在运行:")
        print("   cd D:\\0_workspace\\1_project\\10_Eng_agent\\Milvus")
        print("   docker-compose up -d")
        return False


def test_bge_m3():
    """测试 BGE-M3 模型"""
    print("\n" + "=" * 50)
    print("2. 测试 BGE-M3 模型")
    print("=" * 50)

    try:
        import torch
        print(f"   CUDA 可用: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"   GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("   ⚠️ PyTorch 未安装，将使用 CPU")

    try:
        from src.rag.embedder import BGEM3Embedding

        embedder = BGEM3Embedding(
            model_name="BAAI/bge-m3",
            device="cuda" if torch.cuda.is_available() else "cpu",
        )
        print(f"   ✅ 模型加载成功")

        # 测试向量化
        test_texts = ["Hello world", "你好世界", "Machine learning is great"]
        embeddings = embedder.embed(test_texts)

        print(f"   ✅ 向量化成功，维度: {len(embeddings[0])}")
        return embedder
    except Exception as e:
        print(f"   ❌ 模型测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_milvus_operations(embedder):
    """测试 Milvus 写入和检索"""
    print("\n" + "=" * 50)
    print("3. 测试 Milvus 写入与检索")
    print("=" * 50)

    from pymilvus import (
        connections, Collection, CollectionSchema, FieldSchema, DataType, utility
    )

    collection_name = "test_bge_m3"

    try:
        # 清理旧测试数据
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
            print("   🗑️ 已删除旧测试 Collection")

        # 创建 Collection
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),
        ]

        schema = CollectionSchema(fields, description="BGE-M3 Test Collection")
        collection = Collection(name=collection_name, schema=schema)
        print(f"   ✅ 创建 Collection: {collection_name}")

        # 创建索引
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 256}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        print("   ✅ 创建向量索引")

        # 准备测试数据
        test_texts = [
            "The quick brown fox jumps over the lazy dog.",
            "Machine learning is a subset of artificial intelligence.",
            "Python is a popular programming language.",
            "Natural language processing enables computers to understand text.",
            "Vector databases are optimized for similarity search.",
        ]

        print(f"\n   测试数据 ({len(test_texts)} 条):")
        for i, text in enumerate(test_texts):
            print(f"   [{i+1}] {text[:50]}...")

        # 生成向量
        print("\n   正在生成向量...")
        embeddings = embedder.embed(test_texts)
        print(f"   ✅ 向量生成完成")

        # 插入数据
        collection.insert([test_texts, embeddings])
        collection.flush()
        print(f"   ✅ 数据插入完成")

        # 加载到内存
        collection.load()
        print("   ✅ Collection 已加载到内存")

        # 测试检索
        print("\n   --- 测试向量检索 ---")
        query_text = "AI and machine learning technology"
        query_embedding = embedder.embed([query_text])[0]

        search_params = {"metric_type": "COSINE", "params": {"ef": 64}}
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=3,
            output_fields=["text"]
        )

        print(f"\n   查询: \"{query_text}\"")
        print(f"   Top-3 结果:")
        for i, hit in enumerate(results[0]):
            similarity = 1 - hit.distance
            text = hit.entity.get("text")
            print(f"   [{i+1}] 相似度: {similarity:.4f} | {text[:40]}...")

        # 清理测试数据
        utility.drop_collection(collection_name)
        print(f"\n   🗑️ 已清理测试 Collection")

        return True
    except Exception as e:
        print(f"   ❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "=" * 60)
    print("🚀 Milvus + BGE-M3 集成测试")
    print("=" * 60)

    # 1. 测试 Milvus 连接
    if not test_milvus_connection():
        print("\n❌ Milvus 连接失败，请先启动 Milvus 容器")
        return 1

    # 2. 测试 BGE-M3
    embedder = test_bge_m3()
    if embedder is None:
        print("\n❌ BGE-M3 模型测试失败")
        return 1

    # 3. 测试 Milvus 操作
    if not test_milvus_operations(embedder):
        print("\n❌ Milvus 操作测试失败")
        return 1

    # 总结
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！")
    print("=" * 60)
    print("\n✅ Milvus 部署成功")
    print("✅ BGE-M3 模型加载成功")
    print("✅ 向量写入和检索正常")
    print("\n下一步: 运行知识库构建")
    print("  python src/rag/builder.py -i data/processed/markdown -s <大纲路径>")
    print("=" * 60 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
