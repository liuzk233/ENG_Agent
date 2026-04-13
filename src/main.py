# 文件路径: VocabWeaver/main.py

import os
from utils.llm_client import LLMClient
from agents.orchestrator import run_agent_workflow
from data_pipeline.extractor import load_syllabus_xls

def main():
    print("=========================================")
    print("🚀 VocabWeaver Agent 核心引擎测试启动")
    print("=========================================\n")

    # 1. 初始化基础设施
    print("1. 正在初始化千问大模型客户端...")
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

    # 3. 模拟用户的输入参数
    target_words = ["galaxy", "spaceship", "explore", "danger"]
    style = "科幻"
    
    print(f"\n2. 模拟用户请求:")
    print(f"   - 目标单词: {target_words}")
    print(f"   - 文章风格: {style}")
    print("-----------------------------------------\n")

    # 4. 启动 Agent 引擎进行多轮协作
    # 我们设置最大重试 3 次
    result = run_agent_workflow(
        llm_client=llm_client,
        target_words=target_words,
        style=style,
        syllabus_set=syllabus_set,
        max_retries=3
    )

    # 5. 打印最终结果
    print("\n=========================================")
    print(f"🏁 最终任务状态: {result['status'].upper()}")
    print(f"🔄 总计消耗轮次: {result['attempts']}")
    print("=========================================")
    print("\n📜 最终输出文章:\n")
    print(result['content'])
    print("\n=========================================")

if __name__ == "__main__":
    main()