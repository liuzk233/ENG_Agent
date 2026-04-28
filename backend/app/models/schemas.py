"""
Pydantic 数据模型

定义 API 请求/响应的数据结构
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================
# 请求模型
# ============================================================

class SessionCreateRequest(BaseModel):
    """创建会话请求"""
    user_id: str = Field(..., description="用户标识")
    total_episodes: int = Field(default=1, ge=1, le=10, description="总集数")
    target_words: List[str] = Field(..., min_length=1, description="目标词汇列表")
    style: str = Field(default="adventure", description="文章风格")


class SessionContinueRequest(BaseModel):
    """续写会话请求"""
    user_id: str = Field(..., description="用户标识")
    session_id: str = Field(..., description="会话标识")
    target_words: List[str] = Field(..., min_length=1, description="目标词汇列表")


class WebSocketStartPayload(BaseModel):
    """WebSocket start 消息负载"""
    user_id: str = Field(default="anonymous", description="用户标识")
    target_words: List[str] = Field(..., description="目标词汇列表")
    style: str = Field(default="adventure", description="文章风格")
    total_episodes: int = Field(default=1, ge=1, le=10, description="总集数")


class WebSocketContinuePayload(BaseModel):
    """WebSocket continue 消息负载"""
    target_words: List[str] = Field(..., description="目标词汇列表")


class WebSocketMessage(BaseModel):
    """WebSocket 消息"""
    type: str = Field(..., description="消息类型: start, continue, cancel")
    payload: Optional[dict] = Field(default=None, description="消息负载")


# ============================================================
# 响应模型
# ============================================================

class SessionResponse(BaseModel):
    """会话响应"""
    session_id: str = Field(..., description="会话标识")
    user_id: str = Field(..., description="用户标识")
    status: str = Field(default="active", description="会话状态")
    current_episode: int = Field(default=1, description="当前集数")
    total_episodes: int = Field(default=1, description="总集数")
    style: str = Field(default="adventure", description="文章风格")
    title: Optional[str] = Field(default=None, description="会话标题")
    final_text: Optional[str] = Field(default=None, description="最新章节内容")
    target_words: List[str] = Field(default_factory=list, description="目标词汇")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")


class EpisodeResponse(BaseModel):
    """集数响应"""
    episode_num: int = Field(..., description="集数")
    final_text: Optional[str] = Field(default=None, description="文章内容")
    target_words: List[str] = Field(default_factory=list, description="目标词汇")
    out_of_scope_words: List[str] = Field(default_factory=list, description="超纲词汇")
    retry_count: int = Field(default=0, description="重试次数")
    fallback_mode: bool = Field(default=False, description="兜底模式")


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[SessionResponse] = Field(default_factory=list, description="会话列表")
    total: int = Field(default=0, description="总数")


class GenerateResultResponse(BaseModel):
    """生成结果响应"""
    session_id: str = Field(..., description="会话标识")
    current_episode: int = Field(..., description="当前集数")
    final_text: Optional[str] = Field(default=None, description="文章内容")
    out_of_scope_words: List[str] = Field(default_factory=list, description="超纲词汇")
    retry_count: int = Field(default=0, description="重试次数")
    adjust_count: int = Field(default=0, description="调整次数")
    fallback_mode: bool = Field(default=False, description="兜底模式")


# ============================================================
# WebSocket 推送模型
# ============================================================

class NodeEndPayload(BaseModel):
    """节点完成事件负载"""
    node: str = Field(..., description="节点名称: planner, writer, reviewer, memory")
    status: str = Field(default="success", description="节点状态: success, failed")
    data: Optional[dict] = Field(default=None, description="节点输出数据")


class ProgressPayload(BaseModel):
    """进度更新事件负载"""
    current_episode: int = Field(..., description="当前集数")
    total_episodes: int = Field(..., description="总集数")
    node: str = Field(..., description="当前节点")


class ErrorPayload(BaseModel):
    """错误事件负载"""
    message: str = Field(..., description="错误信息")
    node: Optional[str] = Field(default=None, description="发生错误的节点")


class CompletePayload(BaseModel):
    """完成事件负载"""
    session_id: str = Field(..., description="会话标识")
    current_episode: int = Field(..., description="当前集数")


class WebSocketServerMessage(BaseModel):
    """WebSocket 服务端消息"""
    type: str = Field(..., description="消息类型: node_start, node_end, progress, error, complete")
    payload: dict = Field(..., description="消息负载")


# ============================================================
# 导出
# ============================================================

__all__ = [
    # 请求模型
    "SessionCreateRequest",
    "SessionContinueRequest",
    "WebSocketStartPayload",
    "WebSocketContinuePayload",
    "WebSocketMessage",
    # 响应模型
    "SessionResponse",
    "EpisodeResponse",
    "SessionListResponse",
    "GenerateResultResponse",
    # WebSocket 推送模型
    "NodeEndPayload",
    "ProgressPayload",
    "ErrorPayload",
    "CompletePayload",
    "WebSocketServerMessage",
]
