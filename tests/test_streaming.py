"""
流式生成测试

测试 LangGraph astream 和 WebSocket 实时推送
"""

import pytest
import sys
import os
import asyncio

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ============================================================
# LangGraph Stream Tests
# ============================================================

class TestLangGraphStream:
    """LangGraph 流式执行测试"""

    def test_compile_graph(self):
        """测试 Graph 编译"""
        from graph.graph import compile_graph

        compiled = compile_graph()
        assert compiled is not None

    @pytest.mark.asyncio
    async def test_run_initialize_stream_function_exists(self):
        """测试流式函数存在"""
        from graph.graph import run_initialize_stream

        assert callable(run_initialize_stream)

    @pytest.mark.asyncio
    async def test_run_initialize_stream_basic(self):
        """测试流式生成基本功能"""
        from graph.graph import run_initialize_stream

        # 收集事件
        events = []
        async for event in run_initialize_stream(
            user_id="test_user",
            total_episodes=1,
            target_words=["test"],
            style="adventure",
        ):
            events.append(event)
            # 只收集前几个事件用于测试
            if len(events) >= 2:
                break

        # 验证有事件产生
        assert len(events) > 0

        # 验证事件结构
        for event in events:
            assert isinstance(event, dict)
            # 事件应该是 {node_name: output} 结构
            assert len(event) == 1
            node_name = list(event.keys())[0]
            node_output = event[node_name]
            assert isinstance(node_output, dict)


# ============================================================
# WebSocket Stream Tests (需要服务运行)
# ============================================================

class TestWebSocketStream:
    """WebSocket 流式推送测试"""

    @pytest.mark.asyncio
    async def test_websocket_message_format(self):
        """测试 WebSocket 消息格式"""
        # 定义预期的消息格式
        from pydantic import BaseModel
        from typing import Literal, Optional, Any

        class ServerMessage(BaseModel):
            type: Literal['node_start', 'node_end', 'progress', 'error', 'complete', 'cancelled']
            payload: dict

        # 验证消息格式可以正确解析
        test_messages = [
            {"type": "node_start", "payload": {"node": "initialize"}},
            {"type": "node_end", "payload": {"node": "writer", "status": "success", "data": {}}},
            {"type": "complete", "payload": {"sessionId": "test", "currentEpisode": 1}},
            {"type": "error", "payload": {"message": "test error"}},
        ]

        for msg in test_messages:
            parsed = ServerMessage(**msg)
            assert parsed.type == msg["type"]
            assert parsed.payload == msg["payload"]


# ============================================================
# Connection Manager Tests
# ============================================================

class TestConnectionManager:
    """WebSocket 连接管理器测试"""

    def test_connection_manager_import(self):
        """测试连接管理器可以导入"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from app.api.websocket import ConnectionManager

        manager = ConnectionManager()
        assert manager.active_connections == {}

    def test_connection_manager_disconnect(self):
        """测试连接断开"""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from app.api.websocket import ConnectionManager

        manager = ConnectionManager()
        manager.active_connections["test_session"] = None
        manager.disconnect("test_session")
        assert "test_session" not in manager.active_connections


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
