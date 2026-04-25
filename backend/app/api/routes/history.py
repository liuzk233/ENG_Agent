"""
历史记录 API
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException

from ...models.schemas import (
    SessionResponse,
    EpisodeResponse,
    SessionListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# 历史记录
# ============================================================

@router.get("/users/{user_id}/sessions", response_model=SessionListResponse)
async def get_user_sessions(user_id: str, limit: int = 10, offset: int = 0):
    """
    获取用户会话列表

    - **user_id**: 用户标识
    - **limit**: 返回数量限制
    - **offset**: 偏移量
    """
    logger.info(f"获取用户会话: user={user_id}, limit={limit}")

    try:
        from src.memory.manager import get_memory_manager

        memory = get_memory_manager()
        sessions = memory.list_user_sessions(user_id, limit, offset)
        total = memory.count_user_sessions(user_id)

        return SessionListResponse(
            sessions=[
                SessionResponse(
                    session_id=s["session_id"],
                    user_id=s["user_id"],
                    status=s.get("status", "active"),
                    current_episode=s.get("current_episode", 1),
                    total_episodes=s.get("total_episodes", 1),
                    style=s.get("style", "adventure"),
                    created_at=s.get("created_at"),
                )
                for s in sessions
            ],
            total=total,
        )
    except Exception as e:
        logger.error(f"获取用户会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/episodes", response_model=List[EpisodeResponse])
async def get_session_episodes(session_id: str):
    """
    获取会话的集数列表

    - **session_id**: 会话标识
    """
    logger.info(f"获取会话集数: session={session_id}")

    try:
        from src.memory.manager import get_memory_manager

        memory = get_memory_manager()

        # 首先获取会话信息以获取 user_id
        session = memory.get_session_by_id(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")

        user_id = session.get("user_id", "unknown")
        episodes = memory.list_session_episodes(user_id, session_id)

        return [
            EpisodeResponse(
                episode_num=e.get("episode_num", 1),
                final_text=e.get("transcript") or e.get("final_text", ""),
                target_words=e.get("target_words", []),
                out_of_scope_words=[],
                retry_count=0,
                fallback_mode=False,
            )
            for e in episodes
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话集数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
