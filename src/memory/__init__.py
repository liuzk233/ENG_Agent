"""
Memory Agent 模块

三层记忆管理：
- 故事圣经（静态）
- 状态机（事实）
- 上下文压缩（动态）
"""

from .manager import MemoryManager, get_memory_manager

__all__ = [
    "MemoryManager",
    "get_memory_manager",
]
