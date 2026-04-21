"""
条件边路由逻辑

定义 Graph 中各节点的流转条件。
"""

import logging
from typing import Literal

from .state import GraphState, MAX_RETRIES, MAX_ADJUSTS, MAX_RATIO

logger = logging.getLogger(__name__)

# 路由返回类型定义
RouteAfterReviewer = Literal[
    "memory",
    "writer",
    "annotate_and_pass",
    "planner_adjust",
    "force_annotate",
]

RouteAfterMemory = Literal["end", "waiting"]


def route_after_reviewer(state: GraphState) -> RouteAfterReviewer:
    """
    Reviewer Node 后的路由判断

    判断逻辑：
    1. is_valid=True → memory
    2. is_valid=False:
       - retry < MAX_RETRIES → writer
       - retry >= MAX_RETRIES:
         - ratio <= MAX_RATIO → annotate_and_pass
         - ratio > MAX_RATIO:
           - adjust < MAX_ADJUSTS → planner_adjust
           - adjust >= MAX_ADJUSTS → force_annotate
    """
    is_valid = state.get("is_valid", False)
    retry_count = state.get("retry_count", 0)
    adjust_count = state.get("adjust_count", 0)
    out_of_scope_ratio = state.get("out_of_scope_ratio", 0.0)

    # 1. 审查通过 → 进入 Memory
    if is_valid:
        logger.info("[Router] is_valid=True → memory")
        return "memory"

    # 2. 审查未通过
    logger.info(f"[Router] is_valid=False, retry={retry_count}/{MAX_RETRIES}")

    # 2.1 还有重试机会 → 回到 Writer
    if retry_count < MAX_RETRIES:
        logger.info(f"[Router] retry < {MAX_RETRIES} → writer")
        return "writer"

    # 2.2 达到重试上限，进入兜底判断
    logger.info(f"[Router] retry >= {MAX_RETRIES}, ratio={out_of_scope_ratio:.2%}")

    # 2.2.1 超纲词比例达标 → 标注通过
    if out_of_scope_ratio <= MAX_RATIO:
        logger.info(f"[Router] ratio <= {MAX_RATIO} → annotate_and_pass")
        return "annotate_and_pass"

    # 2.2.2 超纲词比例超标
    logger.info(f"[Router] ratio > {MAX_RATIO}, adjust={adjust_count}/{MAX_ADJUSTS}")

    # 2.2.2.1 还有调整机会 → Planner 调整
    if adjust_count < MAX_ADJUSTS:
        logger.info(f"[Router] adjust < {MAX_ADJUSTS} → planner_adjust")
        return "planner_adjust"

    # 2.2.2.2 达到调整上限 → 强制标注
    logger.info(f"[Router] adjust >= {MAX_ADJUSTS} → force_annotate")
    return "force_annotate"


def route_after_memory(state: GraphState) -> RouteAfterMemory:
    """
    Memory Node 后的路由判断

    判断逻辑：
    - current_episode < total_episodes → waiting（等待用户输入）
    - current_episode >= total_episodes → end
    """
    current_episode = state.get("current_episode", 1)
    total_episodes = state.get("total_episodes", 1)

    logger.info(f"[Router] episode check: {current_episode}/{total_episodes}")

    if current_episode < total_episodes:
        logger.info(f"[Router] episode < total → waiting")
        return "waiting"
    else:
        logger.info(f"[Router] episode >= total → end")
        return "end"
