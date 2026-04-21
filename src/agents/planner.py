"""
Planner Agent

负责：
1. 生成多集大纲
2. 分配目标词汇
3. Planner Adjust 时降低词汇密度
"""

import logging
from typing import List, Tuple, Optional

from src.utils.llm_client import LLMClient
from src.prompts.templates import PLANNER_SYSTEM_PROMPT, get_planning_prompt

logger = logging.getLogger(__name__)


class PlannerAgent:
    """
    Planner Agent

    功能：
    - Initialize 模式：生成 N 集大纲，分配词汇
    - Adjust 模式：降低词汇密度，重新分配
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        初始化 Planner Agent

        Args:
            llm_client: LLM 客户端（可选，用于大纲生成）
        """
        self.llm_client = llm_client

    def generate_outline(
        self,
        total_episodes: int,
        target_words: List[str],
        style: str = "adventure",
    ) -> Tuple[List[str], List[List[str]]]:
        """
        生成大纲和词汇分配

        Args:
            total_episodes: 总集数
            target_words: 目标词汇列表
            style: 风格设定

        Returns:
            Tuple[List[str], List[List[str]]]: (大纲列表, 每集词汇列表)
        """
        logger.info(f"[Planner] 生成 {total_episodes} 集大纲, 风格: {style}")

        # 均匀分配词汇到各集
        word_assignment = self._distribute_words(target_words, total_episodes)

        # 生成大纲（骨架实现，Phase 后续可接入 LLM）
        if self.llm_client:
            outline = self._generate_outline_with_llm(total_episodes, word_assignment, style)
        else:
            # 骨架实现：生成基础大纲
            outline = [
                f"Episode {i+1}: {' '.join(words[:3])}..."
                for i, words in enumerate(word_assignment)
            ]

        logger.info(f"[Planner] 大纲生成完成: {len(outline)} 集")
        return outline, word_assignment

    def adjust_vocabulary_density(
        self,
        current_words: List[str],
        current_episode: int,
        total_episodes: int,
        reduction_ratio: float = 0.5,
    ) -> List[str]:
        """
        降低当前集词汇密度

        Args:
            current_words: 当前集目标词汇
            current_episode: 当前集数
            total_episodes: 总集数
            reduction_ratio: 降低比例

        Returns:
            List[str]: 调整后的词汇列表
        """
        # 保留部分词汇，其余移至后续集数
        keep_count = max(1, int(len(current_words) * (1 - reduction_ratio)))
        adjusted_words = current_words[:keep_count]

        logger.info(
            f"[Planner Adjust] 降低词汇密度: "
            f"{len(current_words)} → {len(adjusted_words)}"
        )

        return adjusted_words

    def _distribute_words(
        self,
        words: List[str],
        episodes: int,
    ) -> List[List[str]]:
        """
        均匀分配词汇到各集

        Args:
            words: 词汇列表
            episodes: 集数

        Returns:
            List[List[str]]: 每集词汇列表
        """
        if not words:
            return [[] for _ in range(episodes)]

        # 边界条件：episodes 为 0
        if episodes <= 0:
            return []

        # 基础分配：每集至少分配一个词
        words_per_episode = max(1, len(words) // episodes)

        assignment = []
        word_idx = 0

        for i in range(episodes):
            # 计算当前集应分配的词汇数
            remaining_episodes = episodes - i
            remaining_words = len(words) - word_idx
            count = max(1, min(words_per_episode, remaining_words))

            episode_words = words[word_idx:word_idx + count]
            assignment.append(episode_words)
            word_idx += count

        # 如果还有剩余词汇，分配到最后一集
        if word_idx < len(words):
            assignment[-1].extend(words[word_idx:])

        return assignment

    def _generate_outline_with_llm(
        self,
        total_episodes: int,
        word_assignment: List[List[str]],
        style: str,
    ) -> List[str]:
        """
        使用 LLM 生成大纲（骨架实现）

        Args:
            total_episodes: 总集数
            word_assignment: 词汇分配
            style: 风格

        Returns:
            List[str]: 大纲列表
        """
        # TODO: Phase 后续实现 LLM 大纲生成
        # 目前返回骨架实现
        return [
            f"Episode {i+1}: {' '.join(words[:3]) if words else 'Story continues...'}"
            for i, words in enumerate(word_assignment)
        ]


def plan_story(
    total_episodes: int,
    target_words: List[str],
    style: str = "adventure",
    llm_client: Optional[LLMClient] = None,
) -> Tuple[List[str], List[List[str]]]:
    """
    便捷函数：生成故事大纲

    Args:
        total_episodes: 总集数
        target_words: 目标词汇
        style: 风格
        llm_client: LLM 客户端

    Returns:
        Tuple[List[str], List[List[str]]]: (大纲列表, 每集词汇列表)
    """
    planner = PlannerAgent(llm_client)
    return planner.generate_outline(total_episodes, target_words, style)


def adjust_words(
    current_words: List[str],
    current_episode: int,
    total_episodes: int,
) -> List[str]:
    """
    便捷函数：调整词汇密度

    Args:
        current_words: 当前词汇
        current_episode: 当前集数
        total_episodes: 总集数

    Returns:
        List[str]: 调整后的词汇
    """
    planner = PlannerAgent()
    return planner.adjust_vocabulary_density(current_words, current_episode, total_episodes)
