"""
集成测试

测试 LangGraph 完整流转和 Agent 协作。
"""

import pytest
import sys
import os
import uuid

# 添加 src 到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph.state import GraphState, MAX_RETRIES, MAX_ADJUSTS, MAX_RATIO
from graph.graph import compile_graph, run_initialize, run_continue
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


# ============================================================
# Graph 编译测试
# ============================================================

class TestGraphCompilation:
    """测试 Graph 编译"""

    def test_compile_success(self):
        """测试 Graph 编译成功"""
        compiled = compile_graph()
        assert compiled is not None

    def test_graph_nodes_exist(self):
        """测试所有节点存在"""
        from graph.graph import build_graph
        graph = build_graph()

        # 验证节点存在
        nodes = list(graph.nodes.keys())
        assert "initialize" in nodes
        assert "load_memory" in nodes
        assert "planner" in nodes
        assert "writer" in nodes
        assert "reviewer" in nodes
        assert "annotate_and_pass" in nodes
        assert "planner_adjust" in nodes
        assert "force_annotate" in nodes
        assert "memory" in nodes


# ============================================================
# 基础流转测试
# ============================================================

class TestBasicFlow:
    """测试基础流转"""

    def test_initialize_mode(self):
        """测试 Initialize 模式完整流转"""
        compiled = compile_graph()

        result = run_initialize(
            compiled,
            user_id="test_user_init",
            total_episodes=2,
            target_words=["explore", "discover"],
            style="adventure",
        )

        # 验证最终状态
        assert result["session_id"] != ""
        assert result["current_episode"] == 2  # 增加了 1
        # 验证有生成内容（draft_text 或 final_text）
        has_content = result.get("final_text") or result.get("draft_text")
        assert has_content is not None
        assert len(has_content) > 100

    def test_continue_mode_requires_session(self):
        """测试 Continue 模式需要有效的 session_id"""
        compiled = compile_graph()

        # 无效 session_id 会创建空会话
        result = run_continue(
            compiled,
            user_id="test_user_continue",
            session_id=str(uuid.uuid4()),
            target_words=["adventure"],
        )

        # load_memory_node 会返回默认状态
        assert result is not None


# ============================================================
# 重试流程测试
# ============================================================

class TestRetryFlow:
    """测试重试流程"""

    def test_retry_count_increment(self):
        """测试 retry_count 递增"""
        # 模拟 Writer 收到 feedback 后重试
        state = {
            "retry_count": 0,
            "feedback_list": ["Remove 'ubiquitous'"],
        }

        # 在 writer_node 中，retry_count 应该在 reviewer_node 之后递增
        # 这里验证 edge 的路由逻辑
        result = route_after_reviewer({
            "is_valid": False,
            "retry_count": 0,
        })

        assert result == "writer"  # 应该回到 writer

    def test_max_retries_triggers_fallback(self):
        """测试达到重试上限触发兜底"""
        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.03,  # 低比例
            "adjust_count": 0,
        }

        result = route_after_reviewer(state)
        assert result == "annotate_and_pass"


# ============================================================
# 兜底机制测试
# ============================================================

class TestFallbackMechanism:
    """测试兜底机制"""

    def test_low_ratio_annotate_and_pass(self):
        """测试低比例兜底：ratio <= 5%"""
        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.03,  # 3% < 5%
            "adjust_count": 0,
        }

        result = route_after_reviewer(state)
        assert result == "annotate_and_pass"

    def test_high_ratio_first_adjust(self):
        """测试高比例首次调整"""
        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.10,  # 10% > 5%
            "adjust_count": 0,
        }

        result = route_after_reviewer(state)
        assert result == "planner_adjust"

    def test_high_ratio_second_adjust(self):
        """测试高比例二次调整"""
        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.10,
            "adjust_count": 1,
        }

        result = route_after_reviewer(state)
        assert result == "planner_adjust"

    def test_high_ratio_force_annotate(self):
        """测试高比例强制标注"""
        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.10,
            "adjust_count": MAX_ADJUSTS,  # 已达上限
        }

        result = route_after_reviewer(state)
        assert result == "force_annotate"

    def test_annotate_and_pass_node(self):
        """测试 annotate_and_pass 节点"""
        state = {
            "draft_text": "This is a test draft.",
            "out_of_scope_words": ["ephemeral", "ubiquitous"],
        }

        result = annotate_and_pass_node(state)

        assert "final_text" in result
        assert result["fallback_mode"] == True
        assert "[Vocabulary Notes]" in result["final_text"]

    def test_force_annotate_node(self):
        """测试 force_annotate 节点"""
        state = {
            "draft_text": "Another test draft.",
            "out_of_scope_words": ["esoteric"],
        }

        result = force_annotate_node(state)

        assert "final_text" in result
        assert result["fallback_mode"] == True

    def test_planner_adjust_node(self):
        """测试 planner_adjust 节点"""
        state = {
            "target_words": ["explore", "discover", "adventure", "mystery", "journey"],
            "current_episode": 1,
            "total_episodes": 3,
            "adjust_count": 0,
        }

        result = planner_adjust_node(state)

        assert result["adjust_count"] == 1
        assert result["retry_count"] == 0
        # 词汇密度应该降低
        assert len(result["target_words"]) < 5


# ============================================================
# 记忆持久化测试
# ============================================================

class TestMemoryPersistence:
    """测试记忆持久化"""

    def test_initialize_creates_session(self):
        """测试 Initialize 创建会话"""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        state = {
            "user_id": user_id,
            "total_episodes": 3,
            "style": "adventure",
            "target_words": ["explore"],
        }

        result = initialize_node(state)

        assert "session_id" in result
        assert result["session_id"] != ""

    def test_memory_node_increments_episode(self):
        """测试 Memory 节点递增集数"""
        state = {
            "user_id": "test_user_memory",
            "session_id": str(uuid.uuid4()),
            "current_episode": 1,
            "total_episodes": 5,
            "final_text": "Test episode text.",
            "story_bible": {},
            "target_words": ["test"],
            "used_words": [],
        }

        result = memory_node(state)

        assert result["current_episode"] == 2


# ============================================================
# 完整流程测试
# ============================================================

class TestFullWorkflow:
    """测试完整流程"""

    def test_single_episode_workflow(self):
        """测试单集完整流程"""
        compiled = compile_graph()

        result = run_initialize(
            compiled,
            user_id=f"test_full_{uuid.uuid4().hex[:8]}",
            total_episodes=1,
            target_words=["explore"],
            style="adventure",
        )

        # 验证流程完成
        assert result["current_episode"] >= 1
        assert "final_text" in result or "draft_text" in result

    def test_multi_episode_workflow(self):
        """测试多集流程"""
        compiled = compile_graph()

        result = run_initialize(
            compiled,
            user_id=f"test_multi_{uuid.uuid4().hex[:8]}",
            total_episodes=2,
            target_words=["explore", "discover", "adventure"],
            style="adventure",
        )

        # 验证第一集完成
        assert result["session_id"] != ""
        assert result["current_episode"] == 2  # 第一集完成后


# ============================================================
# 并发隔离测试
# ============================================================

class TestConcurrencyIsolation:
    """测试并发隔离"""

    def test_user_isolation(self):
        """测试用户隔离"""
        user1 = f"user1_{uuid.uuid4().hex[:8]}"
        user2 = f"user2_{uuid.uuid4().hex[:8]}"

        state1 = initialize_node({
            "user_id": user1,
            "total_episodes": 1,
            "style": "adventure",
            "target_words": ["test"],
        })

        state2 = initialize_node({
            "user_id": user2,
            "total_episodes": 1,
            "style": "scifi",
            "target_words": ["galaxy"],
        })

        # 不同用户应该有不同的 session_id
        assert state1["session_id"] != state2["session_id"]

    def test_session_isolation(self):
        """测试会话隔离"""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"

        state1 = initialize_node({
            "user_id": user_id,
            "total_episodes": 1,
            "style": "adventure",
            "target_words": ["test1"],
        })

        state2 = initialize_node({
            "user_id": user_id,
            "total_episodes": 1,
            "style": "adventure",
            "target_words": ["test2"],
        })

        # 同一用户不同请求应该有不同的 session_id
        assert state1["session_id"] != state2["session_id"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
