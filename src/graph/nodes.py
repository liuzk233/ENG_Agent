"""
Node 函数实现

所有 Node 函数遵循 LangGraph 规范：
- 参数：state: GraphState
- 返回：dict（部分状态更新）

使用真实的 Agent 实现。
"""

import logging
import os
import uuid
from typing import Dict, Any, List

from .state import GraphState, MAX_RETRIES, MAX_RATIO

# Agent 导入
from src.agents.reviewer import check_vocabulary
from src.agents.writer import generate_draft
from src.agents.planner import plan_story, adjust_words
from src.memory.manager import get_memory_manager

# 配置和工具导入
from src.utils.llm_client import LLMClient
from src.utils.config import DASHSCOPE_API_KEY, BASE_URL, MODEL_NAME
from src.rag.retriever import MilvusRAGRetriever
from src.data_pipeline.parsers.extractor import load_syllabus_xls

logger = logging.getLogger(__name__)


# ============================================================
# 共享资源
# ============================================================

_llm_client: LLMClient = None
_rag_retriever: MilvusRAGRetriever = None
_syllabus_set: set = None


def _get_llm_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()  # LLMClient 从 config 读取环境变量
    return _llm_client


def _get_rag_retriever() -> MilvusRAGRetriever:
    """获取 RAG 检索器单例"""
    global _rag_retriever
    if _rag_retriever is None:
        try:
            _rag_retriever = MilvusRAGRetriever(strict_vocabulary=True)
        except Exception as e:
            logger.warning(f"RAG 检索器初始化失败: {e}")
            _rag_retriever = None
    return _rag_retriever


def _get_syllabus_set() -> set:
    """加载大纲词汇表（优先 JSON，回退到 XLS）"""
    global _syllabus_set
    if _syllabus_set is None:
        try:
            # 优先从 JSON 加载
            from src.data_pipeline.parsers.extractor import load_syllabus, get_syllabus_path

            json_path = get_syllabus_path("kaoyan")

            if os.path.exists(json_path):
                from src.data_pipeline.parsers.extractor import load_syllabus_json
                _syllabus_set = load_syllabus_json(json_path)
                logger.info(f"[Syllabus] 从 JSON 加载词汇: {len(_syllabus_set)} 词")
            else:
                # 回退到 XLS
                syllabus_path = "data/raw/syllabus/考研英语词汇表.xls"
                _syllabus_set = load_syllabus_xls(syllabus_path)
                logger.info(f"[Syllabus] 从 XLS 加载词汇: {len(_syllabus_set)} 词")
        except Exception as e:
            logger.warning(f"[Syllabus] 加载失败: {e}")
            _syllabus_set = set()
    return _syllabus_set


# ============================================================
# Initialize Node
# ============================================================

def initialize_node(state: GraphState) -> Dict[str, Any]:
    """
    创建新会话

    输入：user_id, total_episodes, style, target_words
    输出：session_id, story_bible, retry_count=0, adjust_count=0
    """
    logger.info(f"[Initialize] 创建新会话: user={state.get('user_id')}")

    user_id = state.get("user_id", "anonymous")
    total_episodes = state.get("total_episodes", 1)
    target_words = state.get("target_words", [])
    style = state.get("style", "adventure")

    # 生成 session_id
    session_id = str(uuid.uuid4())

    # 初始化故事圣经
    story_bible = {
        "user_id": user_id,
        "session_id": session_id,
        "style": style,
        "characters": [],
        "settings": {},
        "plot_points": [],
    }

    # 创建数据库会话记录
    try:
        memory = get_memory_manager()
        memory.create_session(user_id, session_id, total_episodes, style)
        memory.save_story_bible(user_id, session_id, story_bible)
    except Exception as e:
        logger.warning(f"数据库写入失败: {e}")

    return {
        "session_id": session_id,
        "current_episode": 1,
        "story_bible": story_bible,
        "retry_count": 0,
        "adjust_count": 0,
        "fallback_mode": False,
        "used_words": [],
        "outline": [],
    }


# ============================================================
# Load Memory Node
# ============================================================

def load_memory_node(state: GraphState) -> Dict[str, Any]:
    """
    加载历史状态

    输入：user_id, session_id
    输出：恢复的 GraphState 字段
    """
    user_id = state.get("user_id")
    session_id = state.get("session_id")

    logger.info(f"[Load Memory] 加载会话: user={user_id}, session={session_id}")

    try:
        memory = get_memory_manager()
        full_state = memory.restore_full_state(user_id, session_id)

        if full_state:
            session = full_state.get("session", {})
            story_bible = full_state.get("story_bible", {})

            return {
                "total_episodes": session.get("total_episodes", 1),
                "current_episode": session.get("current_episode", 1),
                "style": session.get("style", "adventure"),
                "story_bible": story_bible,
                "retry_count": 0,
                "adjust_count": 0,
                "fallback_mode": False,
            }
    except Exception as e:
        logger.warning(f"加载历史状态失败: {e}")

    # 默认返回
    return {
        "retry_count": 0,
        "adjust_count": 0,
        "fallback_mode": False,
    }


# ============================================================
# Planner Node
# ============================================================

def planner_node(state: GraphState) -> Dict[str, Any]:
    """
    生成大纲

    输入：target_words, story_bible, total_episodes
    输出：outline, target_words（更新后）
    """
    logger.info(f"[Planner] 生成大纲: episode={state.get('current_episode')}")

    total_episodes = state.get("total_episodes", 1)
    target_words = state.get("target_words", [])
    style = state.get("style", "adventure")

    # 调用 Planner Agent 生成大纲
    outline, word_assignment = plan_story(
        total_episodes=total_episodes,
        target_words=target_words,
        style=style,
        llm_client=None,  # 骨架实现，不使用 LLM
    )

    # 获取当前集的目标词汇
    current_episode = state.get("current_episode", 1)
    if word_assignment and current_episode <= len(word_assignment):
        current_words = word_assignment[current_episode - 1]
    else:
        current_words = target_words

    return {
        "outline": outline,
        "target_words": current_words,
        "retry_count": 0,
    }


# ============================================================
# Writer Node
# ============================================================

def writer_node(state: GraphState) -> Dict[str, Any]:
    """
    生成正文

    输入：outline, feedback_list, previous_summary, target_words, style
    输出：draft_text
    """
    current_episode = state.get("current_episode", 1)
    outline = state.get("outline", [])
    feedback_list = state.get("feedback_list", [])
    previous_summary = state.get("previous_summary", "")
    target_words = state.get("target_words", [])
    style = state.get("style", "adventure")

    logger.info(f"[Writer] 生成正文: episode={current_episode}, feedback_count={len(feedback_list)}")

    # 获取当前集大纲
    episode_outline = outline[current_episode - 1] if outline and current_episode <= len(outline) else ""

    # RAG 检索参考语料
    reference_texts = []
    rag = _get_rag_retriever()
    if rag and rag.should_retrieve(target_words):
        try:
            reference_texts = rag.retrieve(target_words, style=style)
            logger.info(f"[Writer] RAG 检索到 {len(reference_texts)} 条参考语料")
        except Exception as e:
            logger.warning(f"RAG 检索失败: {e}")

    # 调用 Writer Agent 生成正文
    llm = _get_llm_client()
    feedback = "\n".join(feedback_list) if feedback_list else None

    try:
        draft_text = generate_draft(
            llm_client=llm,
            target_words=target_words,
            style=style,
            reference_texts=reference_texts,
            feedback=feedback,
        )
    except Exception as e:
        logger.error(f"生成正文失败: {e}")
        draft_text = f"[Error] 生成失败: {e}"

    return {
        "draft_text": draft_text,
        "is_valid": False,
    }


# ============================================================
# Reviewer Node
# ============================================================

def reviewer_node(state: GraphState) -> Dict[str, Any]:
    """
    词汇校验

    输入：draft_text, target_words
    输出：is_valid, feedback_list, out_of_scope_words, out_of_scope_ratio
    """
    draft_text = state.get("draft_text", "")
    target_words = state.get("target_words", [])

    logger.info(f"[Reviewer] 词汇校验: draft_length={len(draft_text)}")

    # 加载大纲词汇表
    syllabus_set = _get_syllabus_set()

    if not syllabus_set:
        # 大纲词表加载失败，默认通过
        logger.warning("大纲词表未加载，跳过词汇校验")
        return {
            "is_valid": True,
            "feedback_list": [],
            "out_of_scope_words": [],
            "out_of_scope_ratio": 0.0,
        }

    # 调用 Reviewer Agent 词汇校验
    llm = _get_llm_client()

    try:
        is_valid, feedback = check_vocabulary(
            text=draft_text,
            syllabus_set=syllabus_set,
            target_words=target_words,
            llm_client=llm,
        )
    except Exception as e:
        logger.error(f"词汇校验失败: {e}")
        is_valid = True
        feedback = f"校验异常: {e}"

    # 解析超纲词列表
    out_of_scope_words = []
    if not is_valid and feedback:
        import re
        match = re.search(r'\[([^\]]+)\]', feedback)
        if match:
            out_of_scope_words = [w.strip() for w in match.group(1).split(',') if w.strip()]

    # 计算超纲词占比
    total_words = len(draft_text.split())
    out_of_scope_ratio = len(out_of_scope_words) / max(total_words, 1)

    return {
        "is_valid": is_valid,
        "feedback_list": [feedback] if not is_valid else [],
        "out_of_scope_words": out_of_scope_words,
        "out_of_scope_ratio": out_of_scope_ratio,
    }


# ============================================================
# Annotate & Pass Node
# ============================================================

def annotate_and_pass_node(state: GraphState) -> Dict[str, Any]:
    """
    标注中文释义后通过

    输入：draft_text, out_of_scope_words
    输出：final_text, fallback_mode=True
    """
    draft_text = state.get("draft_text", "")
    out_of_scope_words = state.get("out_of_scope_words", [])

    logger.info(f"[Annotate] 标注超纲词: count={len(out_of_scope_words)}")

    # 简单实现：在文本末尾添加词汇表
    # TODO: Phase 后续实现精准标注（调用翻译 API）
    if out_of_scope_words:
        annotation = "\n\n[Vocabulary Notes]\n"
        annotation += "\n".join(f"- {word}" for word in out_of_scope_words)
        final_text = draft_text + annotation
    else:
        final_text = draft_text

    return {
        "final_text": final_text,
        "fallback_mode": True,
    }


# ============================================================
# Planner Adjust Node
# ============================================================

def planner_adjust_node(state: GraphState) -> Dict[str, Any]:
    """
    Planner 降低词汇密度

    输入：target_words, adjust_count
    输出：adjust_count++, retry_count=0
    """
    adjust_count = state.get("adjust_count", 0)
    target_words = state.get("target_words", [])
    current_episode = state.get("current_episode", 1)
    total_episodes = state.get("total_episodes", 1)

    logger.info(f"[Planner Adjust] 降低词汇密度: adjust_count={adjust_count + 1}")

    # 降低词汇密度
    adjusted_words = adjust_words(target_words, current_episode, total_episodes)

    return {
        "target_words": adjusted_words,
        "adjust_count": adjust_count + 1,
        "retry_count": 0,
    }


# ============================================================
# Force Annotate Node
# ============================================================

def force_annotate_node(state: GraphState) -> Dict[str, Any]:
    """
    强制标注通过（已达调整上限）

    输入：draft_text, out_of_scope_words
    输出：final_text, fallback_mode=True
    """
    draft_text = state.get("draft_text", "")
    out_of_scope_words = state.get("out_of_scope_words", [])

    logger.info(f"[Force Annotate] 强制标注通过: count={len(out_of_scope_words)}")

    # 与 annotate_and_pass 相同的处理
    if out_of_scope_words:
        annotation = "\n\n[Vocabulary Notes]\n"
        annotation += "\n".join(f"- {word}" for word in out_of_scope_words)
        final_text = draft_text + annotation
    else:
        final_text = draft_text

    return {
        "final_text": final_text,
        "fallback_mode": True,
    }


# ============================================================
# Memory Node
# ============================================================

def memory_node(state: GraphState) -> Dict[str, Any]:
    """
    保存状态

    输入：final_text, story_bible, current_episode
    输出：持久化状态, current_episode++
    """
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    current_episode = state.get("current_episode", 1)
    total_episodes = state.get("total_episodes", 1)
    final_text = state.get("final_text", "")
    story_bible = state.get("story_bible", {})
    target_words = state.get("target_words", [])
    used_words = state.get("used_words", [])

    logger.info(f"[Memory] 持久化状态: episode={current_episode}/{total_episodes}")

    # 更新已使用词汇
    new_used_words = list(set(used_words + target_words))

    try:
        memory = get_memory_manager()

        # 更新集数
        new_episode = current_episode + 1
        memory.update_episode(user_id, session_id, new_episode)

        # 保存集数状态快照
        memory.save_episode_state(
            user_id=user_id,
            session_id=session_id,
            episode_num=current_episode,
            state={
                "target_words": target_words,
                "final_text": final_text[:500],  # 截断
            },
            transcript=final_text,
            target_words=target_words,
            used_words=new_used_words,
        )

        # 更新故事圣经
        if story_bible:
            story_bible.setdefault("plot_points", []).append({
                "episode": current_episode,
                "summary": final_text[:200],
            })
            memory.save_story_bible(user_id, session_id, story_bible)

        # 更新词汇进度
        for word in target_words:
            memory.update_vocabulary_progress(user_id, session_id, word, final_text[:100])

    except Exception as e:
        logger.warning(f"状态持久化失败: {e}")

    # 生成前情提要
    previous_summary = f"Episode {current_episode} completed."

    return {
        "current_episode": current_episode + 1,
        "used_words": new_used_words,
        "previous_summary": previous_summary,
        "story_bible": story_bible,
    }
