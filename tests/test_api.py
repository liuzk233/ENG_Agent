"""
API 端点测试

测试 FastAPI 后端的 REST API 和 WebSocket
"""

import pytest
import sys
import os
import asyncio
import json

# 添加路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from fastapi.testclient import TestClient


# ============================================================
# Test Client
# ============================================================

@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    from app.main import app
    with TestClient(app) as c:
        yield c


# ============================================================
# Health Check Tests
# ============================================================

class TestHealthCheck:
    """健康检查测试"""

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_root_endpoint(self, client):
        """测试根路由"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


# ============================================================
# Session API Tests
# ============================================================

class TestSessionAPI:
    """会话 API 测试"""

    def test_create_session_validation_error(self, client):
        """测试创建会话参数验证失败"""
        # 缺少必填字段
        response = client.post("/api/sessions", json={
            "user_id": "test_user"
            # 缺少 target_words
        })
        assert response.status_code == 422  # Validation Error

    def test_create_session_missing_words(self, client):
        """测试创建会话缺少词汇"""
        response = client.post("/api/sessions", json={
            "user_id": "test_user",
            "total_episodes": 1,
            "target_words": [],  # 空列表
            "style": "adventure"
        })
        assert response.status_code == 422  # Validation Error

    def test_get_session_not_found(self, client):
        """测试获取不存在的会话"""
        response = client.get("/api/sessions/non-existent-session")
        assert response.status_code == 200  # 返回模拟数据

    def test_delete_session(self, client):
        """测试删除会话"""
        response = client.delete("/api/sessions/test-session-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"


# ============================================================
# History API Tests
# ============================================================

class TestHistoryAPI:
    """历史记录 API 测试"""

    def test_get_user_sessions(self, client):
        """测试获取用户会话列表"""
        response = client.get("/api/users/test_user/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data

    def test_get_session_episodes(self, client):
        """测试获取会话集数"""
        response = client.get("/api/sessions/test-session/episodes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ============================================================
# WebSocket Tests
# ============================================================

class TestWebSocket:
    """WebSocket 测试"""

    def test_websocket_connect(self, client):
        """测试 WebSocket 连接"""
        import uuid
        session_id = str(uuid.uuid4())

        with client.websocket_connect(f"/ws/generate/{session_id}") as websocket:
            # 连接成功
            assert websocket is not None

    def test_websocket_invalid_message(self, client):
        """测试 WebSocket 无效消息"""
        import uuid
        session_id = str(uuid.uuid4())

        with client.websocket_connect(f"/ws/generate/{session_id}") as websocket:
            # 发送无效 JSON
            websocket.send_text("not a json")
            # 接收错误消息
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "无效" in data["payload"]["message"]

    def test_websocket_unknown_message_type(self, client):
        """测试 WebSocket 未知消息类型"""
        import uuid
        session_id = str(uuid.uuid4())

        with client.websocket_connect(f"/ws/generate/{session_id}") as websocket:
            # 发送未知类型消息
            websocket.send_json({"type": "unknown_type"})
            # 接收错误消息
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "未知消息类型" in data["payload"]["message"]

    def test_websocket_cancel(self, client):
        """测试 WebSocket 取消操作"""
        import uuid
        session_id = str(uuid.uuid4())

        with client.websocket_connect(f"/ws/generate/{session_id}") as websocket:
            # 发送取消消息
            websocket.send_json({"type": "cancel"})
            # 接收取消确认
            data = websocket.receive_json()
            assert data["type"] == "cancelled"


# ============================================================
# Run Tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
