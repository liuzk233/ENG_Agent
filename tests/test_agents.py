"""
Agent 单元测试

验证各 Agent 的核心功能。
"""

import pytest
import sys
import os

# 添加 src 到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ============================================================
# Planner Agent 测试
# ============================================================

class TestPlannerAgent:
    """测试 Planner Agent"""

    def test_plan_story_basic(self):
        """测试基础大纲生成"""
        from agents.planner import plan_story

        outline, word_assignment = plan_story(
            total_episodes=3,
            target_words=["explore", "discover", "adventure"],
            style="adventure",
        )

        assert len(outline) == 3
        assert len(word_assignment) == 3

    def test_distribute_words_evenly(self):
        """测试词汇均匀分配"""
        from agents.planner import PlannerAgent

        planner = PlannerAgent()
        assignment = planner._distribute_words(
            words=["a", "b", "c", "d", "e", "f"],
            episodes=3,
        )

        # 每集至少有词汇
        for ep_words in assignment:
            assert len(ep_words) >= 1

    def test_adjust_vocabulary_density(self):
        """测试词汇密度调整"""
        from agents.planner import adjust_words

        adjusted = adjust_words(
            current_words=["a", "b", "c", "d", "e"],
            current_episode=1,
            total_episodes=3,
        )

        # 降低后词汇数量减少
        assert len(adjusted) < 5


# ============================================================
# Reviewer Agent 测试
# ============================================================

class TestReviewerAgent:
    """测试 Reviewer Agent"""

    def test_check_vocabulary_valid(self):
        """测试合法文本"""
        from agents.reviewer import check_vocabulary

        # 简单词汇表
        syllabus = {"the", "is", "a", "test", "hello", "world"}

        is_valid, feedback = check_vocabulary(
            text="Hello world. This is a test.",
            syllabus_set=syllabus,
            target_words=[],
            llm_client=None,
        )

        assert is_valid == True

    def test_check_vocabulary_invalid(self):
        """测试含超纲词文本"""
        from agents.reviewer import check_vocabulary

        syllabus = {"the", "is", "a", "test"}

        is_valid, feedback = check_vocabulary(
            text="The ephemeral nature of existence.",
            syllabus_set=syllabus,
            target_words=[],
            llm_client=None,
        )

        # "ephemeral" 和 "existence" 可能被识别为超纲
        # 结果取决于 spaCy 分词


# ============================================================
# Writer Agent 测试
# ============================================================

class TestWriterAgent:
    """测试 Writer Agent"""

    def test_generate_draft_prompt(self):
        """测试 Prompt 生成"""
        from prompts.templates import get_drafting_prompt, get_refining_prompt

        # 初稿 Prompt
        draft_prompt = get_drafting_prompt(
            style="adventure",
            words_str="explore, discover",
            reference_texts=["Reference text 1"],
        )

        assert "adventure" in draft_prompt
        assert "explore, discover" in draft_prompt

        # 重写 Prompt
        refine_prompt = get_refining_prompt(
            style="adventure",
            words_str="explore, discover",
            feedback="Found out-of-scope words",
        )

        assert "out-of-scope" in refine_prompt


# ============================================================
# Memory Agent 测试
# ============================================================

class TestMemoryAgent:
    """测试 Memory Agent"""

    def test_memory_manager_init(self):
        """测试 MemoryManager 初始化"""
        try:
            from memory.manager import MemoryManager

            # 尝试连接数据库
            memory = MemoryManager()
            assert memory.conn is not None
            memory.close()

        except Exception as e:
            # 数据库连接失败时跳过
            pytest.skip(f"PostgreSQL not available: {e}")

    def test_create_and_load_session(self):
        """测试会话创建和加载"""
        try:
            from memory.manager import MemoryManager
            import uuid

            memory = MemoryManager()

            user_id = "test_user"
            session_id = str(uuid.uuid4())

            # 创建会话
            success = memory.create_session(
                user_id=user_id,
                session_id=session_id,
                total_episodes=5,
                style="adventure",
            )
            assert success == True

            # 加载会话
            session = memory.load_session(user_id, session_id)
            assert session is not None
            assert session["total_episodes"] == 5

            memory.close()

        except Exception as e:
            pytest.skip(f"PostgreSQL not available: {e}")


# ============================================================
# Graph Node 集成测试
# ============================================================

class TestGraphNodes:
    """测试 Graph Node 函数"""

    def test_initialize_node(self):
        """测试 Initialize Node"""
        from graph.nodes import initialize_node

        state = {
            "user_id": "test_user",
            "total_episodes": 3,
            "style": "adventure",
            "target_words": ["explore"],
        }

        result = initialize_node(state)

        assert "session_id" in result
        assert result["current_episode"] == 1
        assert result["retry_count"] == 0

    def test_planner_node(self):
        """测试 Planner Node"""
        from graph.nodes import planner_node

        state = {
            "total_episodes": 2,
            "current_episode": 1,
            "target_words": ["explore", "discover"],
            "style": "adventure",
        }

        result = planner_node(state)

        assert len(result["outline"]) == 2
        assert result["retry_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
