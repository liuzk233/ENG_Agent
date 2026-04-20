# 文件路径: src/utils/config.py
import os
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))

# 加载项目根目录下的 .env 文件
env_path = os.path.join(current_dir, "..", ".env")
load_dotenv(dotenv_path=env_path)

# 阿里云 DashScope API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")

# 检查是否配置了 API Key，防止程序裸奔报错
if not DASHSCOPE_API_KEY:
    raise ValueError("🚨 致命错误: 未在 .env 文件中找到 DASHSCOPE_API_KEY。请检查配置！")

# 模型名称，默认使用你指定的千问最新版
MODEL_NAME = os.getenv("MODEL_NAME", "qwen3.6-plus-2026-04-02")

# API 请求的基础 URL (阿里云兼容 OpenAI 格式的地址)
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# ============================================================
# Milvus 向量数据库配置
# ============================================================

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "vocabweaver_rag")

# 向量存储选择 (chromadb | milvus)
VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "milvus")

# Embedding 配置
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))

# Embedding 后端选择 (dashscope | bge-m3)
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "dashscope")

# BGE-M3 本地模型配置
BGE_M3_MODEL_NAME = os.getenv("BGE_M3_MODEL_NAME", "BAAI/bge-m3")
BGE_M3_USE_FP16 = os.getenv("BGE_M3_USE_FP16", "true").lower() == "true"
BGE_M3_DEVICE = os.getenv("BGE_M3_DEVICE", "cuda")