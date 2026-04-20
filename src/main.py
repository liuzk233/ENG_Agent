# 文件路径: VocabWeaver/main.py
import os
import sys

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from src.utils.llm_client import LLMClient
from src.utils.config import VECTOR_STORE_TYPE
from src.agents.orchestrator import Orchestrator, run_agent_workflow
from src.data_pipeline.parsers.extractor import load_syllabus_xls


def main():
    print("=========================================")
    print("🚀 VocabWeaver Agent 核心引擎测试启动")
    print("=========================================\n")

    # 1. 初始化基础设施
    print("1. 正在�千问大模型客户端...")
    try:
        llm_client = LLMClient()
    except Exception as e:
        print(f"初始化失败: {e}")
        return

    # 2. 加载完整的词汇大纲 (给质检员 Reviewer 用的标尺)
    # 替换为你自己电脑上实际的 .xls 路径
    syllabus_path = r"D:\3_下载与相关数据\xwechat_files\wxid_31zdo0xdsmio22_fcd0\msg\file\2026-04\01.考研英语词汇正序版.xls"
    if not os.path.exists(syllabus_path):
        print(f"🚨 找不到大纲文件: {syllabus_path}")
        return

    syllabus_set = load_syllabus_xls(syllabus_path)
    if not syllabus_set:
        print("🚨 大纲加载失败，测试终止。")
        return

    # 3. 初始化 RAG Retriever（根据配置选择向量数据库）
    print(f"2. 正在初始化 RAG 向量检索器 ({VECTOR_STORE_TYPE})...")
    rag_retriever = None

    try:
        if VECTOR_STORE_TYPE == "milvus":
            from src.rag.retriever import MilvusRAGRetriever
            rag_retriever = MilvusRAGRetriever(
                top_k=5,
                relevance_threshold=0.75,
                strict_vocabulary=True  # 软过滤：只返回纯净语料
            )
        else:
            from src.utils.rag_retriever import RAGRetriever
            rag_retriever = RAGRetriever(
                collection_name="vocabweaver_rag",
                persist_dir="data/vector_store/chromadb",
                top_k=5,
                relevance_threshold=0.75
            )
        print(f"✅ RAG 检索器初始化成功 ({VECTOR_STORE_TYPE})")
    except Exception as e:
        print(f"⚠️ RAG 检索器初始化失败: {e}")
        print("将不使用 RAG 功能继续运行...")
        rag_retriever = None

    # 4. 模拟用户的输入参数
    target_words = ["mandate", "merit", "scope", "desperate"]
    style = "exam_paper"

    print(f"\n3. 模拟用户请求:")
    print(f"   - 目标单词: {target_words}")
    print(f"   - 文章风格: {style}")
    print("-----------------------------------------\n")

    # 5. 启动 Agent 引擎进行多轮协作（使用新的 Orchestrator 类）
    print("4. 启动增强版 RAG Agent 引擎...")
    orchestrator = Orchestrator(
        llm_client=llm_client,
        rag_retriever=rag_retriever,
        max_retries=2  # RAG 已提升首次质量，减少重试次数
    )

    result = orchestrator.execute_workflow(
        target_words=target_words,
        style=style,
        syllabus_set=syllabus_set
    )

    # 6. 打印最终结果
    print("\n=========================================")
    print(f"🏁 最终任务状态: {result['status'].upper()}")
    print(f"🔄 总计消耗轮次: {result['attempts']}")
    print(f"📚 RAG 使用情况: {'是' if result['rag_used'] else '否'}")
    if result['rag_used']:
        print(f"📝 检索到的参考语料数: {result['rag_count']}")
    print(f"🎯 使用风格: {result.get('style', 'N/A')}")
    print("=========================================")
    print("\n📜 最终输出文章:\n")
    print(result['article'])
    print("\n=========================================")


if __name__ == "__main__":
    main()
