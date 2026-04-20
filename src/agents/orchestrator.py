# 文件路径: src/agents/orchestrator.py
import logging
from typing import List, Optional, Union

from .writer import generate_draft
from .reviewer import check_vocabulary
from ..utils.rag_retriever import RAGRetriever
from ..rag.retriever import MilvusRAGRetriever

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrator with Pre-RAG + Semantic Gating"""

    def __init__(
        self,
        llm_client,
        rag_retriever: Optional[Union[RAGRetriever, MilvusRAGRetriever]] = None,
        max_retries: int = 3
    ):
        self.llm_client = llm_client
        self.rag_retriever = rag_retriever
        self.max_retries = max_retries

    def execute_workflow(
        self,
        target_words: List[str],
        style: str = "exam_paper",
        syllabus_set: set = None
    ) -> dict:
        """
        Execute full generation workflow with RAG integration

        Args:
            target_words: 目标单词列表
            style: 文章风格（对应向量数据库中的 category）
            syllabus_set: 词汇大纲集合（用于 Reviewer）

        Returns:
            dict: 包含最终结果和状态的字典
        """
        logger.info(f"🚀 Starting workflow: {len(target_words)} words, style='{style}'")

        # --- Step 1: RAG Retrieval (with Semantic Gating) ---
        reference_texts = None
        rag_used = False

        if self.rag_retriever and self.rag_retriever.should_retrieve(target_words):
            logger.info("📚 Performing RAG retrieval...")
            reference_texts = self.rag_retriever.retrieve(target_words, style)
            if reference_texts:
                rag_used = True
        else:
            logger.info("⚡ Skipping RAG retrieval (Semantic Gating)")

        # --- Step 2: Generate article ---
        logger.info("✍️  Writer Agent generating article...")
        article = generate_draft(
            llm_client=self.llm_client,
            target_words=target_words,
            style=style,
            reference_texts=reference_texts
        )
        logger.info(f"✅ Initial article generated ({len(article)} chars)")

        # --- Step 3: Review ---
        review_result = {
            "passed": False,
            "feedback": "",
            "details": ""
        }

        if syllabus_set:
            review_passed, review_feedback = check_vocabulary(
                article, syllabus_set, target_words, llm_client=self.llm_client
            )
            review_result["passed"] = review_passed
            review_result["feedback"] = review_feedback
            review_result["details"] = review_feedback

        # --- Step 4: Rewrite loop (if needed) ---
        rewrite_count = 0
        while not review_result["passed"] and rewrite_count < self.max_retries:
            rewrite_count += 1
            logger.info(f"🔄 Rewrite #{rewrite_count}/{self.max_retries}")

            # Rewrite based on feedback
            article = generate_draft(
                llm_client=self.llm_client,
                target_words=target_words,
                style=style,
                reference_texts=reference_texts,  # Keep RAG references
                feedback=review_result["feedback"]
            )

            # Review again
            if syllabus_set:
                review_passed, review_feedback = check_vocabulary(
                    article, syllabus_set, target_words, llm_client=self.llm_client
                )
                review_result["passed"] = review_passed
                review_result["feedback"] = review_feedback
                review_result["details"] = review_feedback

        # --- Step 5: Final result ---
        result = {
            'article': article,
            'status': 'passed' if review_result["passed"] else 'failed',
            'passed': review_result["passed"],
            'attempts': rewrite_count + 1,
            'rag_used': rag_used,
            'rag_count': len(reference_texts) if reference_texts else 0,
            'style': style
        }

        logger.info(f"✅ Workflow completed: {'PASSED' if result['passed'] else 'FAILED'} ({rewrite_count} rewrites)")
        return result


# 保持向后兼容的函数
def run_agent_workflow(llm_client, target_words: list, style: str, syllabus_set: set, max_retries: int = 3) -> dict:
    """
    调度器：控制整个"生成-检查-重写"的生命周期。

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
        draft = generate_draft(llm_client, target_words, style, feedback=feedback)

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
        "passed": False,
        "content": draft,  # 返回最后一次尝试的结果
        "attempts": max_retries,
        "reason": "无法在限制次数内消除所有超纲词汇。"
    }
