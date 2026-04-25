"""
性能监控中间件

收集请求响应时间、错误率等指标
"""

import time
import logging
from typing import Callable
from collections import defaultdict
from threading import Lock

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class MetricsCollector:
    """线程安全的指标收集器"""

    def __init__(self):
        self._lock = Lock()
        self._request_count = defaultdict(int)
        self._error_count = defaultdict(int)
        self._latency_sum = defaultdict(float)
        self._latency_count = defaultdict(int)

    def record_request(self, path: str, method: str, status_code: int, latency: float):
        """记录请求指标"""
        key = f"{method}:{path}"

        with self._lock:
            self._request_count[key] += 1
            self._latency_sum[key] += latency
            self._latency_count[key] += 1

            if status_code >= 400:
                self._error_count[key] += 1

    def get_metrics(self) -> dict:
        """获取所有指标"""
        with self._lock:
            metrics = {}
            for key in self._request_count:
                count = self._request_count[key]
                latency_avg = self._latency_sum[key] / count if count > 0 else 0
                error_rate = self._error_count[key] / count if count > 0 else 0

                metrics[key] = {
                    "request_count": count,
                    "error_count": self._error_count[key],
                    "error_rate": round(error_rate, 4),
                    "avg_latency_ms": round(latency_avg * 1000, 2),
                }
            return metrics

    def reset(self):
        """重置所有指标"""
        with self._lock:
            self._request_count.clear()
            self._error_count.clear()
            self._latency_sum.clear()
            self._latency_count.clear()


# 全局指标收集器
metrics_collector = MetricsCollector()


class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    性能监控中间件

    功能：
    - 记录每个请求的响应时间
    - 统计错误率
    - 提供指标查询接口
    """

    # 不监控的路径
    EXCLUDED_PATHS = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 跳过健康检查和文档路径
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # 记录开始时间
        start_time = time.perf_counter()

        try:
            response = await call_next(request)

            # 记录指标
            latency = time.perf_counter() - start_time
            metrics_collector.record_request(
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                latency=latency,
            )

            # 添加响应头
            response.headers["X-Response-Time"] = f"{latency * 1000:.2f}ms"

            return response

        except Exception as e:
            # 记录异常
            latency = time.perf_counter() - start_time
            metrics_collector.record_request(
                path=request.url.path,
                method=request.method,
                status_code=500,
                latency=latency,
            )
            logger.exception(f"Request failed: {request.method} {request.url.path}")
            raise


def get_metrics() -> dict:
    """获取当前指标"""
    return metrics_collector.get_metrics()
