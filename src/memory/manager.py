"""
Memory Agent

负责：
1. PostgreSQL 持久化
2. 会话状态恢复
3. 记忆隔离（user_id + session_id）
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from src.utils.config import (
    POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER,
    POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_URL
)

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Memory Manager

    功能：
    - 创建/读取/更新会话状态
    - 记忆隔离（user_id + session_id）
    - 词汇进度跟踪
    """

    def __init__(self):
        """初始化数据库连接"""
        self.conn = None
        self._connect()

    def _connect(self):
        """连接 PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
            )
            logger.info(f"✅ PostgreSQL 连接成功: {POSTGRES_HOST}:{POSTGRES_PORT}")
        except Exception as e:
            logger.error(f"❌ PostgreSQL 连接失败: {e}")
            raise

    def _ensure_connection(self):
        """确保数据库连接有效"""
        if self.conn is None or self.conn.closed:
            self._connect()

    # ============================================================
    # Session 操作
    # ============================================================

    def create_session(
        self,
        user_id: str,
        session_id: str,
        total_episodes: int,
        style: str = "adventure",
    ) -> bool:
        """
        创建新会话

        Args:
            user_id: 用户ID
            session_id: 会话ID
            total_episodes: 总集数
            style: 风格

        Returns:
            bool: 是否成功
        """
        self._ensure_connection()

        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sessions (user_id, session_id, total_episodes, style, status)
                    VALUES (%s, %s, %s, %s, 'active')
                    ON CONFLICT (user_id, session_id) DO UPDATE
                    SET total_episodes = EXCLUDED.total_episodes,
                        style = EXCLUDED.style,
                        status = 'active',
                        updated_at = NOW()
                """, (user_id, session_id, total_episodes, style))
                self.conn.commit()

            logger.info(f"[Memory] 创建会话: user={user_id}, session={session_id}")
            return True

        except Exception as e:
            logger.error(f"❌ 创建会话失败: {e}")
            self.conn.rollback()
            return False

    def load_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        加载会话状态

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Optional[Dict]: 会话状态，不存在返回 None
        """
        self._ensure_connection()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM sessions
                    WHERE user_id = %s AND session_id = %s
                """, (user_id, session_id))
                result = cur.fetchone()

            if result:
                logger.info(f"[Memory] 加载会话: user={user_id}, session={session_id}")
                return dict(result)
            else:
                logger.warning(f"[Memory] 会话不存在: user={user_id}, session={session_id}")
                return None

        except Exception as e:
            logger.error(f"❌ 加载会话失败: {e}")
            return None

    def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        通过 session_id 获取会话（不需要 user_id）

        Args:
            session_id: 会话ID

        Returns:
            Optional[Dict]: 会话状态，不存在返回 None
        """
        self._ensure_connection()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM sessions
                    WHERE session_id = %s
                """, (session_id,))
                result = cur.fetchone()

            if result:
                logger.info(f"[Memory] 通过ID获取会话: session={session_id}")
                return dict(result)
            else:
                logger.warning(f"[Memory] 会话不存在: session={session_id}")
                return None

        except Exception as e:
            logger.error(f"❌ 获取会话失败: {e}")
            return None

    def update_episode(self, user_id: str, session_id: str, current_episode: int) -> bool:
        """
        更新当前集数

        Args:
            user_id: 用户ID
            session_id: 会话ID
            current_episode: 当前集数

        Returns:
            bool: 是否成功
        """
        self._ensure_connection()

        try:
            with self.conn.cursor() as cur:
                # 更新集数
                cur.execute("""
                    UPDATE sessions
                    SET current_episode = %s, updated_at = NOW()
                    WHERE user_id = %s AND session_id = %s
                """, (current_episode, user_id, session_id))

                # 如果完成所有集数，更新状态
                cur.execute("""
                    UPDATE sessions
                    SET status = 'completed', updated_at = NOW()
                    WHERE user_id = %s AND session_id = %s
                    AND current_episode >= total_episodes
                """, (user_id, session_id))

                self.conn.commit()

            logger.info(f"[Memory] 更新集数: episode={current_episode}")
            return True

        except Exception as e:
            logger.error(f"❌ 更新集数失败: {e}")
            self.conn.rollback()
            return False

    # ============================================================
    # Story Bible 操作
    # ============================================================

    def save_story_bible(
        self,
        user_id: str,
        session_id: str,
        story_bible: Dict[str, Any],
    ) -> bool:
        """
        保存故事圣经

        Args:
            user_id: 用户ID
            session_id: 会话ID
            story_bible: 故事圣经内容

        Returns:
            bool: 是否成功
        """
        self._ensure_connection()

        try:
            # 获取 session_id (UUID)
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT id FROM sessions
                    WHERE user_id = %s AND session_id = %s
                """, (user_id, session_id))
                result = cur.fetchone()

                if not result:
                    logger.error(f"会话不存在: user={user_id}, session={session_id}")
                    return False

                session_uuid = result[0]

                # 插入或更新 story_bible
                cur.execute("""
                    INSERT INTO story_bibles (session_id, content)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id) DO UPDATE
                    SET content = EXCLUDED.content,
                        version = story_bibles.version + 1,
                        updated_at = NOW()
                """, (session_uuid, json.dumps(story_bible)))

                self.conn.commit()

            logger.info(f"[Memory] 保存故事圣经: user={user_id}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存故事圣经失败: {e}")
            self.conn.rollback()
            return False

    def load_story_bible(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        加载故事圣经

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Optional[Dict]: 故事圣经内容
        """
        self._ensure_connection()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT sb.content
                    FROM story_bibles sb
                    JOIN sessions s ON sb.session_id = s.id
                    WHERE s.user_id = %s AND s.session_id = %s
                """, (user_id, session_id))
                result = cur.fetchone()

            if result:
                return result['content']
            return None

        except Exception as e:
            logger.error(f"❌ 加载故事圣经失败: {e}")
            return None

    # ============================================================
    # Episode State 操作
    # ============================================================

    def save_episode_state(
        self,
        user_id: str,
        session_id: str,
        episode_num: int,
        state: Dict[str, Any],
        transcript: str = "",
        target_words: List[str] = None,
        used_words: List[str] = None,
    ) -> bool:
        """
        保存集数状态快照

        Args:
            user_id: 用户ID
            session_id: 会话ID
            episode_num: 集数
            state: 状态快照
            transcript: 完整文本
            target_words: 目标词汇
            used_words: 已使用词汇

        Returns:
            bool: 是否成功
        """
        self._ensure_connection()

        try:
            with self.conn.cursor() as cur:
                # 获取 session UUID
                cur.execute("""
                    SELECT id FROM sessions
                    WHERE user_id = %s AND session_id = %s
                """, (user_id, session_id))
                result = cur.fetchone()

                if not result:
                    return False

                session_uuid = result[0]

                # 插入或更新 episode state
                cur.execute("""
                    INSERT INTO episode_states
                    (session_id, episode_num, state, transcript, target_words, used_words)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, episode_num) DO UPDATE
                    SET state = EXCLUDED.state,
                        transcript = EXCLUDED.transcript,
                        target_words = EXCLUDED.target_words,
                        used_words = EXCLUDED.used_words
                """, (
                    session_uuid,
                    episode_num,
                    json.dumps(state),
                    transcript,
                    json.dumps(target_words or []),
                    json.dumps(used_words or []),
                ))

                self.conn.commit()

            logger.info(f"[Memory] 保存集数状态: episode={episode_num}")
            return True

        except Exception as e:
            logger.error(f"❌ 保存集数状态失败: {e}")
            self.conn.rollback()
            return False

    def load_episode_state(
        self,
        user_id: str,
        session_id: str,
        episode_num: int,
    ) -> Optional[Dict[str, Any]]:
        """
        加载集数状态

        Args:
            user_id: 用户ID
            session_id: 会话ID
            episode_num: 集数

        Returns:
            Optional[Dict]: 状态快照
        """
        self._ensure_connection()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT es.*
                    FROM episode_states es
                    JOIN sessions s ON es.session_id = s.id
                    WHERE s.user_id = %s AND s.session_id = %s AND es.episode_num = %s
                """, (user_id, session_id, episode_num))
                result = cur.fetchone()

            if result:
                return dict(result)
            return None

        except Exception as e:
            logger.error(f"❌ 加载集数状态失败: {e}")
            return None

    # ============================================================
    # Vocabulary Progress 操作
    # ============================================================

    def update_vocabulary_progress(
        self,
        user_id: str,
        session_id: str,
        word: str,
        context: str = "",
    ) -> bool:
        """
        更新词汇进度

        Args:
            user_id: 用户ID
            session_id: 会话ID
            word: 词汇
            context: 使用上下文

        Returns:
            bool: 是否成功
        """
        self._ensure_connection()

        try:
            with self.conn.cursor() as cur:
                # 获取 session UUID
                cur.execute("""
                    SELECT id FROM sessions
                    WHERE user_id = %s AND session_id = %s
                """, (user_id, session_id))
                result = cur.fetchone()

                if not result:
                    return False

                session_uuid = result[0]

                # 更新或插入词汇进度
                cur.execute("""
                    INSERT INTO vocabulary_progress (session_id, word, occurrence_count, contexts, last_used_at)
                    VALUES (%s, %s, 1, %s, NOW())
                    ON CONFLICT (session_id, word) DO UPDATE
                    SET occurrence_count = vocabulary_progress.occurrence_count + 1,
                        contexts = CASE
                            WHEN vocabulary_progress.contexts IS NULL THEN %s
                            ELSE vocabulary_progress.contexts || %s
                        END,
                        last_used_at = NOW()
                """, (
                    session_uuid,
                    word,
                    json.dumps([context]) if context else None,
                    json.dumps([context]) if context else None,
                    json.dumps([context]) if context else None,
                ))

                self.conn.commit()

            return True

        except Exception as e:
            logger.error(f"❌ 更新词汇进度失败: {e}")
            self.conn.rollback()
            return False

    def load_vocabulary_progress(
        self,
        user_id: str,
        session_id: str,
    ) -> Dict[str, Dict[str, Any]]:
        """
        加载词汇进度

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Dict[str, Dict]: 词汇进度字典 {word: {count, contexts, last_used}}
        """
        self._ensure_connection()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT vp.word, vp.occurrence_count, vp.contexts, vp.last_used_at
                    FROM vocabulary_progress vp
                    JOIN sessions s ON vp.session_id = s.id
                    WHERE s.user_id = %s AND s.session_id = %s
                """, (user_id, session_id))
                results = cur.fetchall()

            return {
                row['word']: {
                    'count': row['occurrence_count'],
                    'contexts': row['contexts'] or [],
                    'last_used': row['last_used_at'].isoformat() if row['last_used_at'] else None,
                }
                for row in results
            }

        except Exception as e:
            logger.error(f"❌ 加载词汇进度失败: {e}")
            return {}

    # ============================================================
    # 完整状态恢复
    # ============================================================

    def restore_full_state(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        恢复完整会话状态

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            Optional[Dict]: 完整状态
        """
        # 加载会话元信息
        session = self.load_session(user_id, session_id)
        if not session:
            return None

        # 加载故事圣经
        story_bible = self.load_story_bible(user_id, session_id) or {}

        # 加载最新集数状态
        current_episode = session.get('current_episode', 1)
        if current_episode > 1:
            episode_state = self.load_episode_state(user_id, session_id, current_episode - 1)
        else:
            episode_state = None

        # 加载词汇进度
        vocab_progress = self.load_vocabulary_progress(user_id, session_id)

        return {
            'session': session,
            'story_bible': story_bible,
            'last_episode_state': episode_state,
            'vocabulary_progress': vocab_progress,
        }

    def close(self):
        """关闭数据库连接"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("[Memory] PostgreSQL 连接已关闭")

    # ============================================================
    # 列表查询
    # ============================================================

    def list_user_sessions(
        self,
        user_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取用户会话列表

        Args:
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[Dict]: 会话列表
        """
        self._ensure_connection()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT session_id, user_id, status, current_episode, total_episodes, style, created_at
                    FROM sessions
                    WHERE user_id = %s
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                """, (user_id, limit, offset))
                results = cur.fetchall()

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"❌ 获取用户会话列表失败: {e}")
            return []

    def count_user_sessions(self, user_id: str) -> int:
        """
        统计用户会话数量

        Args:
            user_id: 用户ID

        Returns:
            int: 会话数量
        """
        self._ensure_connection()

        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*) FROM sessions WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()

            return result[0] if result else 0

        except Exception as e:
            logger.error(f"❌ 统计用户会话数量失败: {e}")
            return 0

    def list_session_episodes(
        self,
        user_id: str,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """
        获取会话的所有集数

        Args:
            user_id: 用户ID
            session_id: 会话ID

        Returns:
            List[Dict]: 集数列表
        """
        self._ensure_connection()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT es.episode_num, es.transcript, es.target_words, es.used_words
                    FROM episode_states es
                    JOIN sessions s ON es.session_id = s.id
                    WHERE s.user_id = %s AND s.session_id = %s
                    ORDER BY es.episode_num ASC
                """, (user_id, session_id))
                results = cur.fetchall()

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"❌ 获取会话集数列表失败: {e}")
            return []


# ============================================================
# 全局单例
# ============================================================

_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """获取 MemoryManager 单例"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager
