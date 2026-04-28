"""
会话管理 API
Updated: 2026-04-25 - v2
"""

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.concurrency import run_in_threadpool

from ...models.schemas import (
    SessionCreateRequest,
    SessionResponse,
    GenerateResultResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# 依赖注入
# ============================================================

def get_compiled_graph(request):
    """获取已编译的 Graph"""
    graph = request.app.state.compiled_graph
    if graph is None:
        raise HTTPException(status_code=503, detail="LangGraph 未初始化")
    return graph


# ============================================================
# 会话管理
# ============================================================

@router.post("/sessions", response_model=GenerateResultResponse)
async def create_session(
    request: SessionCreateRequest,
    graph = Depends(lambda r: get_compiled_graph(r))
):
    """
    创建新会话并生成文章

    - **user_id**: 用户标识
    - **total_episodes**: 总集数 (1-10)
    - **target_words**: 目标词汇列表
    - **style**: 文章风格
    """
    logger.info(f"创建会话: user={request.user_id}, words={request.target_words}")

    # 生成 session_id
    session_id = str(uuid.uuid4())

    try:
        # 在线程池中运行同步的 LangGraph
        from src.graph.graph import run_initialize

        result = await run_in_threadpool(
            run_initialize,
            compiled_graph=graph,
            user_id=request.user_id,
            total_episodes=request.total_episodes,
            target_words=request.target_words,
            style=request.style,
        )

        # 更新 session_id
        result["session_id"] = result.get("session_id", session_id)

        return GenerateResultResponse(
            session_id=result.get("session_id", session_id),
            current_episode=result.get("current_episode", 1),
            final_text=result.get("final_text") or result.get("draft_text"),
            out_of_scope_words=result.get("out_of_scope_words", []),
            retry_count=result.get("retry_count", 0),
            adjust_count=result.get("adjust_count", 0),
            fallback_mode=result.get("fallback_mode", False),
        )

    except Exception as e:
        logger.exception("生成失败")
        raise HTTPException(status_code=500, detail=f"生成失败: {str(e)}")


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    获取会话状态

    - **session_id**: 会话标识
    """
    from src.memory.manager import MemoryManager

    manager = MemoryManager()
    try:
        # 使用新方法通过 session_id 获取会话
        session_data = manager.get_session_by_id(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="会话不存在")

        user_id = session_data.get('user_id', '')
        current_episode = session_data.get('current_episode', 1)

        # 获取最新章节内容
        episode_state = None
        if current_episode > 0:
            episode_state = manager.load_episode_state(
                user_id,
                session_id,
                current_episode
            )

        return SessionResponse(
            session_id=session_id,
            user_id=user_id,
            status=session_data.get('status', 'active'),
            current_episode=current_episode,
            total_episodes=session_data.get('total_episodes', 1),
            style=session_data.get('style', 'adventure'),
            title=session_data.get('title'),
            final_text=episode_state.get('final_text') if episode_state else None,
            target_words=episode_state.get('target_words', []) if episode_state else [],
        )
    finally:
        manager.close()


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话

    - **session_id**: 会话标识
    """
    from src.memory.manager import MemoryManager

    manager = MemoryManager()
    try:
        success = manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除会话失败")

        logger.info(f"删除会话: {session_id}")
        return {"status": "deleted", "session_id": session_id}
    finally:
        manager.close()


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    title: Optional[str] = Query(None, description="新标题")
):
    """
    更新会话

    - **session_id**: 会话标识
    - **title**: 新标题
    """
    from src.memory.manager import MemoryManager

    manager = MemoryManager()
    try:
        if title:
            success = manager.update_session_title(session_id, title)
            if not success:
                raise HTTPException(status_code=500, detail="更新会话失败")

        logger.info(f"更新会话: {session_id}, title={title}")
        return {"status": "updated", "session_id": session_id, "title": title}
    finally:
        manager.close()
