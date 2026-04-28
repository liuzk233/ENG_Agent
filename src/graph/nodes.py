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
import time
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
from src.data_pipeline.parsers.extractor import load_syllabus

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
    """加载大纲词汇表（从标准 JSON 文件）"""
    global _syllabus_set
    if _syllabus_set is None:
        try:
            _syllabus_set = load_syllabus("kaoyan")
            logger.info(f"[Syllabus] 加载词汇: {len(_syllabus_set)} 词")
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

    输入：user_id, total_episodes, style, target_words, session_id (可选)
    输出：session_id, story_bible, retry_count=0, adjust_count=0
    """
    logger.info(f"[Initialize] 创建新会话: user={state.get('user_id')}")

    user_id = state.get("user_id", "anonymous")
    total_episodes = state.get("total_episodes", 1)
    target_words = state.get("target_words", [])
    style = state.get("style", "adventure")

    # 使用前端传来的 session_id，如果不存在则生成新的
    session_id = state.get("session_id") or str(uuid.uuid4())

    # 初始化故事圣经
    story_bible = {
        "user_id": user_id,
        "session_id": session_id,
        "style": style,
        "characters": [],
        "settings": [],
        "plot_points": [],
        "items": [],
        "outline": [],  # 预留大纲字段
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
            last_episode_state = full_state.get("last_episode_state", {})
            # 从聚合结果获取已使用的词汇
            used_words = full_state.get("used_words", [])

            # 生成前情提要
            previous_summary = ""
            if last_episode_state:
                last_text = last_episode_state.get("transcript", "")
                if last_text:
                    previous_summary = last_text[:500]  # 使用上一章的最后500字符作为摘要

            # 数据库中 current_episode 存储的是"已完成的章节号"
            # 续写时需要返回"下一章节号"，所以 +1
            next_episode = session.get("current_episode", 0) + 1
            logger.info(f"[Load Memory] 恢复成功: next_episode={next_episode}, style={session.get('style')}")

            # 从 story_bible 提取 outline
            outline = story_bible.get("outline", [])

            return {
                "total_episodes": session.get("total_episodes", 1),
                "current_episode": next_episode,
                "style": session.get("style", "adventure"),
                "story_bible": story_bible,
                "outline": outline,
                "used_words": used_words,
                "previous_summary": previous_summary,
                "retry_count": 0,
                "adjust_count": 0,
                "fallback_mode": False,
            }
    except Exception as e:
        logger.warning(f"加载历史状态失败: {e}")

    # 默认返回（加载失败时返回初始状态）
    return {
        "total_episodes": 1,
        "current_episode": 1,
        "style": "adventure",
        "story_bible": {},
        "outline": [],
        "used_words": [],
        "previous_summary": "",
        "retry_count": 0,
        "adjust_count": 0,
        "fallback_mode": False,
    }


# ============================================================
# Planner Node
# ============================================================

def planner_node(state: GraphState) -> Dict[str, Any]:
    """
    生成大纲（仅第一集生成）

    输入：target_words, story_bible, total_episodes, current_episode
    输出：outline (或复用现有), episode_outline (当前集大纲)
    """
    logger.info(f"[Planner] 检查大纲: episode={state.get('current_episode')}")

    total_episodes = state.get("total_episodes", 1)
    current_episode = state.get("current_episode", 1)
    target_words = state.get("target_words", [])
    style = state.get("style", "adventure")
    story_bible = state.get("story_bible", {})

    # 从 story_bible 取已有大纲
    outline = story_bible.get("outline", [])

    # 仅在第一集且无大纲时生成
    if not outline and current_episode == 1:
        logger.info("[Planner] 第一集，生成新大纲")
        llm = _get_llm_client()
        outline, word_assignment = plan_story(
            total_episodes=total_episodes,
            target_words=target_words,
            style=style,
            llm_client=llm,
            story_bible=story_bible,
        )
        # 存入 story_bible
        story_bible = {**story_bible, "outline": outline}
    elif outline:
        logger.info("[Planner] 复用现有大纲")
    else:
        # 非 first 集但无大纲（异常情况），生成降级大纲
        logger.warning("[Planner] 非第一集但无大纲，生成降级大纲")
        outline = [f"Episode {i+1}: Story continues..." for i in range(total_episodes)]
        story_bible = {**story_bible, "outline": outline}

    # 取当前集大纲
    episode_outline = outline[current_episode - 1] if outline and current_episode <= len(outline) else ""

    return {
        "outline": outline,
        "episode_outline": episode_outline,
        "story_bible": story_bible,
        "retry_count": 0,
    }


# ============================================================
# Writer Node
# ============================================================

def writer_node(state: GraphState) -> Dict[str, Any]:
    """
    生成正文

    输入：outline, episode_outline, feedback_list, previous_summary, target_words, style, story_bible
    输出：draft_text
    """
    start_time = time.time()
    current_episode = state.get("current_episode", 1)
    outline = state.get("outline", [])
    episode_outline = state.get("episode_outline", "")  # 优先使用
    feedback_list = state.get("feedback_list", [])
    previous_summary = state.get("previous_summary", "")
    target_words = state.get("target_words", [])
    style = state.get("style", "adventure")
    story_bible = state.get("story_bible", {})

    logger.info(f"[Writer] 生成正文: episode={current_episode}, feedback_count={len(feedback_list)}")

    # 获取当前集大纲（优先使用 episode_outline，否则从 outline 列表中提取）
    if not episode_outline:
        episode_outline = outline[current_episode - 1] if outline and current_episode <= len(outline) else ""

    # RAG 检索参考语料
    rag_start = time.time()
    reference_texts = []
    rag = _get_rag_retriever()
    if rag and rag.should_retrieve(target_words, style=style):
        try:
            reference_texts = rag.retrieve(target_words, style=style)
            logger.info(f"[Writer] RAG 检索到 {len(reference_texts)} 条参考语料, 耗时: {time.time() - rag_start:.2f}s")
        except Exception as e:
            logger.warning(f"RAG 检索失败: {e}")

    # 调用 Writer Agent 生成正文
    llm_start = time.time()
    llm = _get_llm_client()
    feedback = "\n".join(feedback_list) if feedback_list else None

    try:
        draft_text = generate_draft(
            llm_client=llm,
            target_words=target_words,
            style=style,
            reference_texts=reference_texts,
            feedback=feedback,
            story_bible=story_bible,
            previous_summary=previous_summary,
            episode_outline=episode_outline,
        )
        logger.info(f"[Writer] LLM 生成完成, 耗时: {time.time() - llm_start:.2f}s")
    except Exception as e:
        logger.error(f"生成正文失败: {e}")
        draft_text = f"[Error] 生成失败: {e}"

    logger.info(f"[Writer] 总耗时: {time.time() - start_time:.2f}s")

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
    from src.agents.extractor import extract_story_elements, update_story_bible

    start_time = time.time()
    user_id = state.get("user_id")
    session_id = state.get("session_id")
    current_episode = state.get("current_episode", 1)
    total_episodes = state.get("total_episodes", 1)
    # 优先使用 final_text，否则使用 draft_text
    final_text = state.get("final_text") or state.get("draft_text", "")
    story_bible = state.get("story_bible", {})
    target_words = state.get("target_words", [])
    used_words = state.get("used_words", [])

    logger.info(f"[Memory] 持久化状态: episode={current_episode}/{total_episodes}")

    # 更新已使用词汇
    new_used_words = list(set(used_words + target_words))

    try:
        memory = get_memory_manager()

        # 提取故事元素并更新 story_bible
        extract_start = time.time()
        try:
            llm = _get_llm_client()
            extraction = extract_story_elements(llm, final_text, story_bible)
            story_bible = update_story_bible(story_bible, extraction, current_episode)
            logger.info(
                f"[Memory] 提取到: {len(extraction.get('new_characters', []))} 角色, "
                f"{len(extraction.get('new_settings', []))} 地点, "
                f"{len(extraction.get('new_items', []))} 物品, 耗时: {time.time() - extract_start:.2f}s"
            )
        except Exception as e:
            logger.warning(f"故事元素提取失败: {e}")

        # 保存集数状态快照（数据库存储已完成的章节数）
        memory.save_episode_state(
            user_id=user_id,
            session_id=session_id,
            episode_num=current_episode,
            transcript=final_text,
            target_words=target_words,
            used_words=new_used_words,
        )

        # 更新数据库中的 current_episode 为已完成的章节数
        memory.update_episode(user_id, session_id, current_episode)

        # 保存更新后的故事圣经
        memory.save_story_bible(user_id, session_id, story_bible)

    except Exception as e:
        logger.warning(f"状态持久化失败: {e}")

    logger.info(f"[Memory] 总耗时: {time.time() - start_time:.2f}s")

    # 生成前情提要（使用最新章节的摘要）
    plot_points = story_bible.get("plot_points", [])
    if plot_points:
        previous_summary = plot_points[-1].get("summary", f"Episode {current_episode} completed.")
    else:
        previous_summary = f"Episode {current_episode} completed."

    return {
        "current_episode": current_episode + 1,
        "used_words": new_used_words,
        "previous_summary": previous_summary,
        "story_bible": story_bible,
        "final_text": final_text,  # 确保 final_text 被更新
    }
