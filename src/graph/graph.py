"""
Graph 组装与编译

将所有 Node 和 Edge 组装成完整的 LangGraph。
"""

import logging
from typing import Literal, TypedDict, Optional

from langgraph.graph import StateGraph, START, END

from .state import GraphState
from .nodes import (
    initialize_node,
    load_memory_node,
    planner_node,
    writer_node,
    reviewer_node,
    annotate_and_pass_node,
    planner_adjust_node,
    force_annotate_node,
    memory_node,
)
from .edges import route_after_reviewer, route_after_memory

logger = logging.getLogger(__name__)


# ============================================================
# 输入模式定义
# ============================================================

class InitializeInput(TypedDict):
    """Initialize 模式输入"""
    user_id: str
    total_episodes: int
    target_words: list[str]
    style: str


class ContinueInput(TypedDict):
    """Continue 模式输入"""
    user_id: str
    session_id: str
    target_words: list[str]


# ============================================================
# Entry Point 路由
# ============================================================

def route_entry_point(state: GraphState) -> Literal["initialize", "load_memory"]:
    """
    根据 session_id 判断入口模式

    - session_id 为空 → Initialize 模式
    - session_id 不为空 → Continue 模式
    """
    session_id = state.get("session_id", "")
    if session_id:
        logger.info(f"[Entry Router] Continue 模式: session={session_id}")
        return "load_memory"
    else:
        logger.info("[Entry Router] Initialize 模式")
        return "initialize"


# ============================================================
# Graph 构建函数
# ============================================================

def build_graph() -> StateGraph:
    """
    构建 LangGraph

    结构：
    START → [条件边] → initialize_node / load_memory_node
          → planner_node → writer_node → reviewer_node
          → [条件边] → memory_node / writer / annotate_and_pass / planner_adjust / force_annotate
          → memory_node → [条件边] → END
    """
    # 创建 StateGraph
    graph = StateGraph(GraphState)

    # ============================================================
    # 添加 Node
    # ============================================================
    graph.add_node("initialize", initialize_node)
    graph.add_node("load_memory", load_memory_node)
    graph.add_node("planner", planner_node)
    graph.add_node("writer", writer_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("annotate_and_pass", annotate_and_pass_node)
    graph.add_node("planner_adjust", planner_adjust_node)
    graph.add_node("force_annotate", force_annotate_node)
    graph.add_node("memory", memory_node)

    # ============================================================
    # Entry Point 条件边
    # ============================================================
    graph.add_conditional_edges(
        START,
        route_entry_point,
        {
            "initialize": "initialize",
            "load_memory": "load_memory",
        }
    )

    # ============================================================
    # 添加 Edge
    # ============================================================

    # Initialize → Planner
    graph.add_edge("initialize", "planner")

    # Load Memory → Planner
    graph.add_edge("load_memory", "planner")

    # Planner → Writer
    graph.add_edge("planner", "writer")

    # Writer → Reviewer
    graph.add_edge("writer", "reviewer")

    # Reviewer → 条件边
    graph.add_conditional_edges(
        "reviewer",
        route_after_reviewer,
        {
            "memory": "memory",
            "writer": "writer",
            "annotate_and_pass": "annotate_and_pass",
            "planner_adjust": "planner_adjust",
            "force_annotate": "force_annotate",
        }
    )

    # Annotate & Pass → Memory
    graph.add_edge("annotate_and_pass", "memory")

    # Planner Adjust → Planner
    graph.add_edge("planner_adjust", "planner")

    # Force Annotate → Memory
    graph.add_edge("force_annotate", "memory")

    # Memory → 条件边
    graph.add_conditional_edges(
        "memory",
        route_after_memory,
        {
            "end": END,
            "waiting": END,  # waiting 也结束当前流程，等待下次输入
        }
    )

    logger.info("Graph 构建完成")

    return graph


def compile_graph() -> any:
    """
    编译 Graph

    Returns:
        CompiledGraph: 可执行的 Graph
    """
    graph = build_graph()
    compiled = graph.compile()
    logger.info("Graph 编译完成")
    return compiled


# ============================================================
# 运行 Graph
# ============================================================

def run_initialize(
    compiled_graph,
    user_id: str,
    total_episodes: int,
    target_words: list[str],
    style: str = "adventure",
) -> dict:
    """
    Initialize 模式运行

    Args:
        compiled_graph: 编译后的 Graph
        user_id: 用户ID
        total_episodes: 总集数
        target_words: 目标词汇
        style: 风格

    Returns:
        最终状态
    """
    # 初始状态
    initial_state = {
        "user_id": user_id,
        "session_id": "",
        "total_episodes": total_episodes,
        "current_episode": 1,
        "style": style,
        "outline": [],
        "target_words": target_words,
        "used_words": [],
        "draft_text": "",
        "final_text": "",
        "is_valid": False,
        "feedback_list": [],
        "out_of_scope_words": [],
        "out_of_scope_ratio": 0.0,
        "retry_count": 0,
        "adjust_count": 0,
        "fallback_mode": False,
        "story_bible": {},
        "previous_summary": "",
    }

    logger.info(f"[Run Initialize] user={user_id}, episodes={total_episodes}")

    # 设置 Entry Point 并运行
    config = {"entrypoint": "initialize"}
    result = compiled_graph.invoke(initial_state, config)

    return result


def run_continue(
    compiled_graph,
    user_id: str,
    session_id: str,
    target_words: list[str],
) -> dict:
    """
    Continue 模式运行

    Args:
        compiled_graph: 编译后的 Graph
        user_id: 用户ID
        session_id: 会话ID
        target_words: 目标词汇

    Returns:
        最终状态
    """
    # 初始状态（session_id 由 load_memory_node 加载）
    initial_state = {
        "user_id": user_id,
        "session_id": session_id,
        "total_episodes": 0,
        "current_episode": 0,
        "style": "",
        "outline": [],
        "target_words": target_words,
        "used_words": [],
        "draft_text": "",
        "final_text": "",
        "is_valid": False,
        "feedback_list": [],
        "out_of_scope_words": [],
        "out_of_scope_ratio": 0.0,
        "retry_count": 0,
        "adjust_count": 0,
        "fallback_mode": False,
        "story_bible": {},
        "previous_summary": "",
    }

    logger.info(f"[Run Continue] user={user_id}, session={session_id}")

    # 设置 Entry Point 并运行
    config = {"entrypoint": "load_memory"}
    result = compiled_graph.invoke(initial_state, config)

    return result


# ============================================================
# 便捷函数
# ============================================================

def create_and_compile():
    """创建并编译 Graph（便捷函数）"""
    return compile_graph()
