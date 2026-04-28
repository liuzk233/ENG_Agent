"""
端到端测试

测试完整的用户场景。
"""

import pytest
import sys
import os
import uuid
import time

# 添加 src 到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph.state import GraphState, MAX_RETRIES, MAX_ADJUSTS, MAX_RATIO
from graph.graph import compile_graph, run_initialize, run_continue
from graph.edges import route_after_reviewer
from graph.nodes import (
    initialize_node,
    planner_node,
    reviewer_node,
    memory_node,
    planner_adjust_node,
)
from memory.manager import MemoryManager, get_memory_manager


# ============================================================
# 断点续写测试
# ============================================================

class TestResumeStory:
    """测试断点续写"""

    @pytest.fixture
    def memory(self):
        """获取 MemoryManager 实例"""
        try:
            return get_memory_manager()
        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")

    def test_create_and_resume(self, memory):
        """测试创建故事后断点续写"""
        user_id = f"resume_test_{uuid.uuid4().hex[:8]}"
        session_id = str(uuid.uuid4())

        # Step 1: 创建会话
        success = memory.create_session(
            user_id=user_id,
            session_id=session_id,
            total_episodes=3,
            style="adventure",
        )
        assert success == True

        # Step 2: 保存第一集状态
        memory.save_episode_state(
            user_id=user_id,
            session_id=session_id,
            episode_num=1,
            transcript="Full episode 1 transcript...",
            target_words=["explore"],
            used_words=["explore"],
        )

        # Step 3: 更新集数
        memory.update_episode(user_id, session_id, 2)

        # Step 4: 恢复状态
        full_state = memory.restore_full_state(user_id, session_id)

        assert full_state is not None
        assert full_state["session"]["current_episode"] == 2
        assert full_state["session"]["total_episodes"] == 3

        # 清理
        memory.close()

    def test_resume_preserves_story_bible(self, memory):
        """测试断点续写保留故事圣经"""
        user_id = f"bible_test_{uuid.uuid4().hex[:8]}"
        session_id = str(uuid.uuid4())

        # 创建会话
        memory.create_session(user_id, session_id, 5, "scifi")

        # 保存故事圣经
        story_bible = {
            "characters": ["Alice", "Bob"],
            "settings": {"location": "Mars"},
            "plot_points": [{"episode": 1, "summary": "Landing on Mars"}],
        }
        memory.save_story_bible(user_id, session_id, story_bible)

        # 恢复
        full_state = memory.restore_full_state(user_id, session_id)

        assert full_state["story_bible"]["characters"] == ["Alice", "Bob"]
        assert full_state["story_bible"]["settings"]["location"] == "Mars"

        memory.close()


# ============================================================
# 兜底机制端到端测试
# ============================================================

class TestFallbackE2E:
    """测试兜底机制端到端流程"""

    def test_annotate_and_pass_flow(self):
        """测试标注通过完整流程"""
        compiled = compile_graph()

        # 模拟高重试次数状态
        # 实际测试中，这需要 mock reviewer 返回 is_valid=False
        # 这里主要验证路由逻辑
        from graph.edges import route_after_reviewer

        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.03,
            "adjust_count": 0,
        }

        result = route_after_reviewer(state)
        assert result == "annotate_and_pass"

    def test_planner_adjust_flow(self):
        """测试 Planner 调整完整流程"""
        from graph.nodes import planner_adjust_node

        state = {
            "target_words": ["word1", "word2", "word3", "word4", "word5"],
            "current_episode": 1,
            "total_episodes": 3,
            "adjust_count": 0,
        }

        result = planner_adjust_node(state)

        assert result["adjust_count"] == 1
        assert result["retry_count"] == 0

    def test_force_annotate_flow(self):
        """测试强制标注完整流程"""
        from graph.edges import route_after_reviewer

        state = {
            "is_valid": False,
            "retry_count": MAX_RETRIES,
            "out_of_scope_ratio": 0.15,
            "adjust_count": MAX_ADJUSTS,
        }

        result = route_after_reviewer(state)
        assert result == "force_annotate"


# ============================================================
# 多集连载测试
# ============================================================

class TestMultiEpisode:
    """测试多集连载"""

    def test_episode_progression(self):
        """测试集数递增"""
        compiled = compile_graph()

        result = run_initialize(
            compiled,
            user_id=f"multi_ep_{uuid.uuid4().hex[:8]}",
            total_episodes=3,
            target_words=["explore", "discover", "adventure", "mystery", "journey"],
            style="adventure",
        )

        # 验证第一集完成
        assert result["current_episode"] == 2
        assert result["session_id"] != ""

    def test_outline_generation(self):
        """测试大纲生成"""
        from graph.nodes import planner_node

        state = {
            "total_episodes": 5,
            "current_episode": 1,
            "target_words": ["explore", "discover", "adventure", "mystery", "journey", "treasure"],
            "style": "adventure",
        }

        result = planner_node(state)

        assert len(result["outline"]) == 5
        assert result["retry_count"] == 0


# ============================================================
# 错误处理测试
# ============================================================

class TestErrorHandling:
    """测试错误处理"""

    def test_missing_syllabus_graceful_degradation(self):
        """测试大纲词表缺失时优雅降级"""
        from graph.nodes import _get_syllabus_set

        # 第一次调用可能为空（如果文件不存在）
        syllabus = _get_syllabus_set()

        # 不应该抛出异常
        assert syllabus is not None  # 可能是空 set

    def test_rag_failure_graceful_degradation(self):
        """测试 RAG 失败时优雅降级"""
        from graph.nodes import _get_rag_retriever

        # RAG 检索器可能为 None（如果 Milvus 未启动）
        rag = _get_rag_retriever()

        # 不应该抛出异常
        # writer_node 会检查 rag 是否为 None

    def test_memory_failure_graceful_handling(self):
        """测试数据库失败时优雅处理"""
        from graph.nodes import initialize_node

        # 使用有效的 user_id
        state = {
            "user_id": "test_error_handling",
            "total_episodes": 1,
            "style": "adventure",
            "target_words": ["test"],
        }

        # 即使数据库不可用，也应该返回有效的状态
        result = initialize_node(state)

        assert "session_id" in result


# ============================================================
# 性能基准测试
# ============================================================

class TestPerformanceBenchmarks:
    """测试性能基准"""

    def test_initialize_node_latency(self):
        """测试 Initialize 节点延迟"""
        start = time.time()

        initialize_node({
            "user_id": "perf_test",
            "total_episodes": 1,
            "style": "adventure",
            "target_words": ["test"],
        })

        elapsed = time.time() - start

        # 初始化应该在 1 秒内完成
        assert elapsed < 1.0, f"Initialize took {elapsed:.2f}s"

    def test_planner_node_latency(self):
        """测试 Planner 节点延迟"""
        start = time.time()

        planner_node({
            "total_episodes": 3,
            "current_episode": 1,
            "target_words": ["explore", "discover", "adventure"],
            "style": "adventure",
        })

        elapsed = time.time() - start

        # Planner 应该在 0.1 秒内完成（骨架实现）
        assert elapsed < 0.1, f"Planner took {elapsed:.2f}s"

    def test_edge_routing_latency(self):
        """测试条件边路由延迟"""
        start = time.time()

        for _ in range(100):
            route_after_reviewer({
                "is_valid": False,
                "retry_count": 3,
                "out_of_scope_ratio": 0.10,
                "adjust_count": 1,
            })

        elapsed = time.time() - start

        # 100 次路由应该在 0.01 秒内完成
        assert elapsed < 0.01, f"100 routes took {elapsed:.4f}s"


# ============================================================
# 集成冒烟测试
# ============================================================

class TestSmokeTests:
    """冒烟测试：快速验证核心功能"""

    def test_graph_compiles(self):
        """测试 Graph 可编译"""
        compiled = compile_graph()
        assert compiled is not None

    def test_initialize_creates_session(self):
        """测试 Initialize 创建会话"""
        result = initialize_node({
            "user_id": "smoke_test",
            "total_episodes": 1,
            "style": "adventure",
            "target_words": ["test"],
        })

        assert "session_id" in result
        assert result["session_id"] != ""

    def test_planner_generates_outline(self):
        """测试 Planner 生成大纲"""
        result = planner_node({
            "total_episodes": 3,
            "current_episode": 1,
            "target_words": ["explore"],
            "style": "adventure",
        })

        assert len(result["outline"]) == 3

    def test_reviewer_validates_text(self):
        """测试 Reviewer 校验文本"""
        result = reviewer_node({
            "draft_text": "This is a simple test.",
            "target_words": ["test"],
        })

        assert "is_valid" in result

    def test_memory_persists_state(self):
        """测试 Memory 持久化状态"""
        result = memory_node({
            "user_id": "smoke_test",
            "session_id": str(uuid.uuid4()),
            "current_episode": 1,
            "total_episodes": 3,
            "final_text": "Test text.",
            "story_bible": {},
            "target_words": ["test"],
            "used_words": [],
        })

        assert result["current_episode"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])  # -x: 遇到第一个失败就停止
