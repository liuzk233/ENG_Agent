"""
日志中间件

结构化请求日志记录
"""

import time
import json
import logging
from typing import Callable
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    功能：
    - 记录请求/响应日志
    - 结构化 JSON 格式输出
    - 可配置日志级别
    """

    # 不记录日志的路径
    EXCLUDED_PATHS = {"/health", "/metrics"}

    # 敏感字段（不记录）
    SENSITIVE_FIELDS = {"password", "token", "api_key", "secret"}

    def __init__(self, app, log_level: str = "INFO"):
        super().__init__(app)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过健康检查路径
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # 记录请求
        request_id = request.headers.get("X-Request-ID", "-")
        start_time = time.perf_counter()

        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": "request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", "-"),
        }

        logger.log(self.log_level, json.dumps(log_data))

        try:
            response = await call_next(request)

            # 记录响应
            latency = time.perf_counter() - start_time

            response_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "response",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(latency * 1000, 2),
            }

            # 根据状态码选择日志级别
            if response.status_code >= 500:
                logger.error(json.dumps(response_log))
            elif response.status_code >= 400:
                logger.warning(json.dumps(response_log))
            else:
                logger.log(self.log_level, json.dumps(response_log))

            # 添加请求 ID 到响应头
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # 记录异常
            latency = time.perf_counter() - start_time
            error_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "error",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "latency_ms": round(latency * 1000, 2),
            }
            logger.error(json.dumps(error_log))
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端真实 IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 直接连接
        if request.client:
            return request.client.host

        return "-"
