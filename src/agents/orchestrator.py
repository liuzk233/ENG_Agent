# 文件路径: src/agents/orchestrator.py
from src.agents.writer import generate_draft
from src.agents.reviewer import check_vocabulary

def run_agent_workflow(llm_client, target_words: list, style: str, syllabus_set: set, max_retries: int = 3) -> dict:
    """
    调度器：控制整个“生成-检查-重写”的生命周期。
    
    :param max_retries: 最大重试次数。Agent 开发极其重要的一点：必须设置熔断机制，防止死循环烧光 API 余额。
    :return: 包含最终结果和状态的字典
    """
    print(f"🚀 开始编织文章 (目标词: {target_words}, 风格: {style})")
    
    feedback = None
    attempt = 1
    
    # 这就是经典的 Agent 执行循环 (Agentic Loop)
    while attempt <= max_retries:
        print(f"\n--- 🔄 第 {attempt} 轮迭代 ---")
        
        # 1. 创作阶段 (Actor)
        draft = generate_draft(llm_client, target_words, style, feedback)
        
        # 2. 质检阶段 (Critic)
        passed, new_feedback = check_vocabulary(draft, syllabus_set, target_words, llm_client=llm_client)
        
        if passed:
            print("✅ 审核通过！文章生成完毕。")
            return {
                "status": "success",
                "content": draft,
                "attempts": attempt
            }
        else:
            print(f"❌ 审核失败，发现超纲词。生成反馈并发回重作...")
            print(f"反馈内容: {new_feedback}")
            # 更新 feedback，让 Writer 在下一轮知道自己错在哪
            feedback = new_feedback
            attempt += 1
            
    # 如果循环结束还没通过，触发熔断
    print(f"\n⚠️ 达到最大重试次数 ({max_retries})，任务中止。")
    return {
        "status": "failed",
        "content": draft,  # 返回最后一次尝试的结果
        "attempts": max_retries,
        "reason": "无法在限制次数内消除所有超纲词汇。"
    }