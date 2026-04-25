"""
WebSocket 实时通信

实现生成流程的实时进度推送
"""

import uuid
import logging
import asyncio
import json
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================
# WebSocket 连接管理器
# ============================================================

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        """接受连接"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket 连接: {session_id}")

    def disconnect(self, session_id: str):
        """断开连接"""
        self.active_connections.pop(session_id, None)
        logger.info(f"WebSocket 断开: {session_id}")

    async def send_json(self, session_id: str, data: dict):
        """发送 JSON 消息"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(data)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                self.disconnect(session_id)

    async def broadcast(self, data: dict):
        """广播消息"""
        for session_id in list(self.active_connections.keys()):
            await self.send_json(session_id, data)


# 全局连接管理器
manager = ConnectionManager()


# ============================================================
# WebSocket 端点
# ============================================================

@router.websocket("/ws/generate/{session_id}")
async def websocket_generate(websocket: WebSocket, session_id: str):
    """
    WebSocket 生成端点

    消息格式：
    - 客户端发送: {"type": "start", "payload": {...}}
    - 服务端推送: {"type": "node_end", "payload": {...}}
    """
    await manager.connect(session_id, websocket)

    try:
        while True:
            # 接收消息
            raw_message = await websocket.receive_text()
            try:
                message = json.loads(raw_message)
            except json.JSONDecodeError:
                await manager.send_json(session_id, {
                    "type": "error",
                    "payload": {"message": "无效的 JSON 格式"}
                })
                continue

            msg_type = message.get("type")
            payload = message.get("payload", {})

            logger.info(f"收到消息: type={msg_type}")

            if msg_type == "start":
                await run_generation(session_id, payload, websocket)

            elif msg_type == "continue":
                await run_continue(session_id, payload, websocket)

            elif msg_type == "cancel":
                await manager.send_json(session_id, {
                    "type": "cancelled",
                    "payload": {"session_id": session_id}
                })
                break

            else:
                await manager.send_json(session_id, {
                    "type": "error",
                    "payload": {"message": f"未知消息类型: {msg_type}"}
                })

    except WebSocketDisconnect:
        manager.disconnect(session_id)

    except Exception as e:
        logger.exception("WebSocket 异常")
        await manager.send_json(session_id, {
            "type": "error",
            "payload": {"message": str(e)}
        })
        manager.disconnect(session_id)


# ============================================================
# 生成流程
# ============================================================

async def run_generation(session_id: str, payload: dict, websocket: WebSocket):
    """
    执行 LangGraph 生成流程（流式）
    """
    user_id = payload.get("user_id", "anonymous")
    target_words = payload.get("target_words", [])
    style = payload.get("style", "adventure")
    # 兼容 snake_case 和 camelCase
    total_episodes = payload.get("total_episodes") or payload.get("totalEpisodes", 1)

    logger.info(f"开始生成: session={session_id}, words={target_words}, episodes={total_episodes}")

    # 初始化状态
    initial_state = {
        "user_id": user_id,
        "session_id": session_id,
        "target_words": target_words,
        "style": style,
        "total_episodes": total_episodes,
        "current_episode": 1,
        "retry_count": 0,
        "adjust_count": 0,
        "fallback_mode": False,
        "used_words": [],
        "outline": [],
        "feedback_list": [],
    }

    try:
        # 导入 LangGraph 流式函数
        from src.graph.graph import run_initialize_stream

        # 发送开始事件
        await manager.send_json(session_id, {
            "type": "node_start",
            "payload": {"node": "initialize"}
        })

        # 使用流式函数执行
        final_state = initial_state.copy()
        node_names = {
            "initialize": "初始化",
            "load_memory": "加载记忆",
            "planner": "大纲规划",
            "writer": "内容生成",
            "reviewer": "词汇审查",
            "annotate_and_pass": "标注通过",
            "planner_adjust": "词汇调整",
            "force_annotate": "强制通过",
            "memory": "状态保存",
        }

        async for event in run_initialize_stream(
            compiled_graph=None,  # 由函数内部编译
            user_id=user_id,
            session_id=session_id,  # 传递前端生成的 session_id
            total_episodes=total_episodes,
            target_words=target_words,
            style=style,
        ):
            node_name = list(event.keys())[0]
            node_output = event[node_name]

            logger.info(f"节点完成: {node_name}")

            # 推送节点完成事件
            await manager.send_json(session_id, {
                "type": "node_end",
                "payload": {
                    "node": node_name,
                    "node_label": node_names.get(node_name, node_name),
                    "status": "success",
                    "data": {
                        "retry_count": node_output.get("retry_count"),
                        "is_valid": node_output.get("is_valid"),
                        "out_of_scope_words": node_output.get("out_of_scope_words", []),
                        "draft_text": (node_output.get("draft_text") or "")[:200],
                        "current_episode": node_output.get("current_episode"),
                    }
                }
            })

            # 更新最终状态
            if isinstance(node_output, dict):
                final_state = {**final_state, **node_output}

        # 推送完成事件
        final_text = None
        if final_state:
            final_text = final_state.get("final_text") or final_state.get("draft_text")

        # 获取实际完成的集数（current_episode 在 memory_node 中已递增，需要减1）
        completed_episode = (final_state.get("current_episode", 1) - 1) if final_state else 1
        total_episodes = final_state.get("total_episodes", 1) if final_state else 1

        await manager.send_json(session_id, {
            "type": "complete",
            "payload": {
                "session_id": session_id,
                "current_episode": completed_episode,  # 实际完成的集数
                "total_episodes": total_episodes,
                "next_episode": completed_episode + 1,  # 下一集（可选用于续写）
                "final_text": final_text,
                "out_of_scope_words": final_state.get("out_of_scope_words", []) if final_state else [],
                "retry_count": final_state.get("retry_count", 0) if final_state else 0,
                "fallback_mode": final_state.get("fallback_mode", False) if final_state else False,
            }
        })

        logger.info(f"生成完成: session={session_id}")

    except Exception as e:
        logger.exception("生成失败")
        await manager.send_json(session_id, {
            "type": "error",
            "payload": {"message": str(e)}
        })


async def run_continue(session_id: str, payload: dict, websocket: WebSocket):
    """
    执行续写流程
    """
    # 兼容 snake_case 和 camelCase
    target_words = payload.get("target_words") or payload.get("targetWords", [])
    user_id = payload.get("user_id", "anonymous")

    logger.info(f"续写: session={session_id}, words={target_words}")

    try:
        # 导入续写流式函数
        from src.graph.graph import run_continue_stream

        # 发送开始事件
        await manager.send_json(session_id, {
            "type": "node_start",
            "payload": {"node": "load_memory"}
        })

        # 节点名称映射
        node_names = {
            "initialize": "初始化",
            "load_memory": "加载记忆",
            "planner": "大纲规划",
            "writer": "内容生成",
            "reviewer": "词汇审查",
            "annotate_and_pass": "标注通过",
            "planner_adjust": "词汇调整",
            "force_annotate": "强制通过",
            "memory": "状态保存",
        }

        # 使用续写流式函数执行
        final_state = {}
        async for event in run_continue_stream(
            compiled_graph=None,
            user_id=user_id,
            session_id=session_id,
            target_words=target_words,
        ):
            node_name = list(event.keys())[0]
            node_output = event[node_name]

            logger.info(f"[续写] 节点完成: {node_name}")

            # 推送节点完成事件
            await manager.send_json(session_id, {
                "type": "node_end",
                "payload": {
                    "node": node_name,
                    "node_label": node_names.get(node_name, node_name),
                    "status": "success",
                    "data": {
                        "retry_count": node_output.get("retry_count"),
                        "is_valid": node_output.get("is_valid"),
                        "out_of_scope_words": node_output.get("out_of_scope_words", []),
                        "current_episode": node_output.get("current_episode"),
                    }
                }
            })

            # 更新最终状态
            if isinstance(node_output, dict):
                final_state = {**final_state, **node_output}

        # 推送完成事件
        final_text = None
        if final_state:
            final_text = final_state.get("final_text") or final_state.get("draft_text")

        # 获取实际完成的集数（current_episode 在 memory_node 中已递增，需要减1）
        completed_episode = (final_state.get("current_episode", 1) - 1) if final_state else 1
        total_episodes = final_state.get("total_episodes", 1) if final_state else 1

        await manager.send_json(session_id, {
            "type": "complete",
            "payload": {
                "session_id": session_id,
                "current_episode": completed_episode,
                "total_episodes": total_episodes,
                "next_episode": completed_episode + 1 if completed_episode < total_episodes else None,
                "final_text": final_text,
                "out_of_scope_words": final_state.get("out_of_scope_words", []) if final_state else [],
                "retry_count": final_state.get("retry_count", 0) if final_state else 0,
                "fallback_mode": final_state.get("fallback_mode", False) if final_state else False,
            }
        })

        logger.info(f"续写完成: session={session_id}, episode={completed_episode}")

    except Exception as e:
        logger.exception("续写失败")
        await manager.send_json(session_id, {
            "type": "error",
            "payload": {"message": str(e)}
        })
