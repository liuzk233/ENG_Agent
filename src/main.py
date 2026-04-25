"""
CLI 入口

使用 LangGraph 流程运行 VocabWeaver。
"""

import os
import sys
import uuid
import logging

# 修复 Windows 终端编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

from src.utils.config import VECTOR_STORE_TYPE
from src.data_pipeline.parsers.extractor import load_syllabus_json
from src.graph.graph import compile_graph, run_initialize, run_continue

# 标准 JSON 大纲文件路径
SYLLABUS_JSON_PATH = "data/processed/dicts/kaoyan_syllabus.json"


def main():
    """主入口函数"""
    print("=========================================")
    print("🚀 VocabWeaver LangGraph 引擎测试启动")
    print("=========================================\n")

    # 1. 加载大纲词表
    print("1. 正在加载大纲词表...")
    if not os.path.exists(SYLLABUS_JSON_PATH):
        print(f"🚨 找不到大纲文件: {SYLLABUS_JSON_PATH}")
        return

    syllabus_set = load_syllabus_json(SYLLABUS_JSON_PATH)
    if not syllabus_set:
        print("🚨 大纲加载失败，测试终止。")
        return

    print(f"✅ 大纲词表加载成功: {len(syllabus_set)} 词\n")

    # 2. 编译 Graph
    print("2. 正在编译 LangGraph...")
    try:
        compiled_graph = compile_graph()
        print("✅ Graph 编译成功\n")
    except Exception as e:
        print(f"🚨 Graph 编译失败: {e}")
        return

    # 3. 模拟用户输入
    user_id = f"cli_user_{uuid.uuid4().hex[:8]}"
    target_words = ["explore", "discover", "adventure"]
    style = "adventure"
    total_episodes = 2

    print(f"3. 模拟用户请求:")
    print(f"   - 用户 ID: {user_id}")
    print(f"   - 目标单词: {target_words}")
    print(f"   - 文章风格: {style}")
    print(f"   - 总集数: {total_episodes}")
    print("-----------------------------------------\n")

    # 4. 运行 Initialize 模式
    print("4. 启动 Initialize 模式...")
    print("   (Writer 生成 → Reviewer 校验 → 循环/通过)\n")

    try:
        result = run_initialize(
            compiled_graph,
            user_id=user_id,
            total_episodes=total_episodes,
            target_words=target_words,
            style=style,
        )

        # 5. 打印结果
        print("\n=========================================")
        print("🏁 流程完成")
        print("=========================================")
        print(f"📌 Session ID: {result.get('session_id', 'N/A')}")
        print(f"📌 当前集数: {result.get('current_episode', 'N/A')}/{total_episodes}")
        print(f"📌 重试次数: {result.get('retry_count', 0)}")
        print(f"📌 调整次数: {result.get('adjust_count', 0)}")
        print(f"📌 兜底模式: {result.get('fallback_mode', False)}")

        if result.get('out_of_scope_words'):
            print(f"📌 超纲词: {result['out_of_scope_words']}")

        print("\n📜 最终输出:")
        print("-" * 40)
        final_text = result.get('final_text') or result.get('draft_text', '[无输出]')
        print(final_text[:500] + "..." if len(final_text) > 500 else final_text)
        print("-" * 40)

        # 6. 演示 Continue 模式
        print("\n5. 演示 Continue 模式（断点续写）...")
        session_id = result.get('session_id')

        if session_id:
            continue_result = run_continue(
                compiled_graph,
                user_id=user_id,
                session_id=session_id,
                target_words=["mystery", "journey"],
            )

            print(f"✅ Continue 完成")
            print(f"📌 当前集数: {continue_result.get('current_episode', 'N/A')}/{total_episodes}")

    except Exception as e:
        logger.exception("流程执行失败")
        print(f"\n🚨 执行失败: {e}")

    print("\n=========================================")
    print("🏁 测试结束")
    print("=========================================")


if __name__ == "__main__":
    main()
