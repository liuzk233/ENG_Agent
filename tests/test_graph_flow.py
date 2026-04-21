"""
Graph 流转测试

验证 LangGraph 骨架的正确性。
"""

import pytest
import sys
import os

# 添加 src 到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph.state import GraphState, MAX_RETRIES, MAX_ADJUSTS, MAX_RATIO
from graph.nodes import (
    initialize_node,
    planner_node,
    writer_node,
    reviewer_node,
    annotate_and_pass_node,
    planner_adjust_node,
    force_annotate_node,
    memory_node,
)
from graph.edges import route_after_reviewer, route_after_memory
from graph.graph import compile_graph, run_initialize


# ============================================================
# Node 测试
# ============================================================

class TestNodes:
    """测试 Node 函数返回正确的状态更新"""

    def test_initialize_node(self):
        """测试 Initialize Node"""
        state = {
            "user_id": "test_user",
            "total_episodes": 5,
            "style": "adventure",
            "target_words": ["explore", "discover"],
        }
        result = initialize_node(state)

        assert "session_id" in result
        assert result["current_episode"] == 1
        assert result["retry_count"] == 0
        assert result["adjust_count"] == 0
        assert "story_bible" in result

    def test_planner_node(self):
        """测试 Planner Node"""
        state = {
            "total_episodes": 3,
            "current_episode": 1,
            "target_words": ["explore"],
        }
        result = planner_node(state)

        assert len(result["outline"]) == 3
        assert result["retry_count"] == 0

    def test_writer_node(self):
        """测试 Writer Node"""
        state = {
            "current_episode": 1,
            "outline": ["Episode 1: The Beginning"],
            "feedback_list": [],
        }
        result = writer_node(state)

        assert "draft_text" in result
        # LLM 生成的文本长度应大于 100 字符
        assert len(result["draft_text"]) > 100
        assert result["is_valid"] == False

    def test_reviewer_node(self):
        """测试 Reviewer Node"""
        state = {
            "draft_text": "This is a test draft.",
            "target_words": ["test"],
        }
        result = reviewer_node(state)

        assert result["is_valid"] == True
        assert result["out_of_scope_ratio"] == 0.0

    def test_memory_node(self):
        """测试 Memory Node"""
        state = {
            "current_episode": 1,
            "total_episodes": 5,
            "final_text": "Final episode text.",
        }
        result = memory_node(state)

        assert result["current_episode"] == 2
        assert "Episode 1" in result["previous_summary"]


# ============================================================
# Edge 测试
# ============================================================

class TestEdges:
    """测试条件边路由逻辑"""

    def test_route_after_reviewer_valid(self):
        """测试审查通过 → memory"""
        state = {
            "is_valid": True,
        }
        result = route_after_reviewer(state)
        assert result == "memory"

    def test_route_after_reviewer_retry(self):
        """测试重试 → writer"""
        state = {
            "is_valid": False,
            "retry_count": 0,
        }
        result = route_after_reviewer(state)
        assert result == "writer"

    def test_route_after_reviewer_annotate_and_pass(self):
        """测试兜底：低比例 → annotate_and_pass"""
        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.03,  # < MAX_RATIO
        }
        result = route_after_reviewer(state)
        assert result == "annotate_and_pass"

    def test_route_after_reviewer_planner_adjust(self):
        """测试兜底：高比例首次调整 → planner_adjust"""
        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.10,  # > MAX_RATIO
            "adjust_count": 0,  # < MAX_ADJUSTS
        }
        result = route_after_reviewer(state)
        assert result == "planner_adjust"

    def test_route_after_reviewer_force_annotate(self):
        """测试兜底：高比例达到上限 → force_annotate"""
        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.10,  # > MAX_RATIO
            "adjust_count": MAX_ADJUSTS,  # >= MAX_ADJUSTS
        }
        result = route_after_reviewer(state)
        assert result == "force_annotate"

    def test_route_after_memory_waiting(self):
        """测试未完成 → waiting"""
        state = {
            "current_episode": 1,
            "total_episodes": 5,
        }
        result = route_after_memory(state)
        assert result == "waiting"

    def test_route_after_memory_end(self):
        """测试已完成 → end"""
        state = {
            "current_episode": 5,
            "total_episodes": 5,
        }
        result = route_after_memory(state)
        assert result == "end"


# ============================================================
# Graph 流转测试
# ============================================================

class TestGraphFlow:
    """测试完整 Graph 流转"""

    def test_compile_graph(self):
        """测试 Graph 编译"""
        compiled = compile_graph()
        assert compiled is not None

    def test_initialize_flow(self):
        """测试 Initialize 模式完整流转"""
        compiled = compile_graph()

        result = run_initialize(
            compiled,
            user_id="test_user",
            total_episodes=2,
            target_words=["explore", "discover"],
            style="adventure",
        )

        # 验证最终状态
        assert result["session_id"] != ""
        assert result["current_episode"] == 2  # 增加了 1
        assert "final_text" in result


# ============================================================
# 死循环保护测试
# ============================================================

class TestDeadLoopProtection:
    """测试死循环保护机制"""

    def test_max_retries_constant(self):
        """测试 MAX_RETRIES 常量"""
        assert MAX_RETRIES == 5

    def test_max_adjusts_constant(self):
        """测试 MAX_ADJUSTS 常量"""
        assert MAX_ADJUSTS == 2

    def test_max_ratio_constant(self):
        """测试 MAX_RATIO 常量"""
        assert MAX_RATIO == 0.05


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
