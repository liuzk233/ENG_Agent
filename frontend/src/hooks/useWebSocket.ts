/**
 * WebSocket Hook
 *
 * 封装 WebSocket 连接管理、消息收发、重连机制
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import type { ClientMessage, ServerMessage, StartPayload, ContinuePayload } from '@/types';

interface UseWebSocketOptions {
  sessionId: string | null;
  onMessage?: (message: ServerMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  sendStart: (payload: StartPayload) => void;
  sendContinue: (payload: ContinuePayload) => void;
  sendCancel: () => void;
  disconnect: () => void;
  reconnect: () => void;  // 新增：手动重连方法
  /** 等待连接建立后执行回调 */
  whenConnected: (callback: () => void, timeout?: number) => Promise<boolean>;
}

export function useWebSocket({
  sessionId,
  onMessage,
  onConnect,
  onDisconnect,
  reconnectAttempts = 5,
  reconnectInterval = 3000,
}: UseWebSocketOptions): UseWebSocketReturn {
  console.log('[WebSocket] hook 渲染, sessionId:', sessionId);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const manualCloseRef = useRef(false);

  // 使用 ref 存储回调，避免依赖循环
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);

  // 更新 ref
  useEffect(() => {
    onMessageRef.current = onMessage;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
  });

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  // 清理重连定时器
  const clearReconnectTimeout = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  // 连接 WebSocket
  const connect = useCallback(() => {
    if (!sessionId || manualCloseRef.current) return;

    const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/generate/${sessionId}`;

    console.log('[WebSocket] 正在连接:', wsUrl);
    setIsConnecting(true);

    try {
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[WebSocket] 连接成功:', sessionId);
        setIsConnected(true);
        setIsConnecting(false);
        reconnectCountRef.current = 0;
        manualCloseRef.current = false;
        onConnectRef.current?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: ServerMessage = JSON.parse(event.data);
          console.log('[WebSocket] 收到消息:', message.type, message);
          onMessageRef.current?.(message);
        } catch (error) {
          console.error('[WebSocket] 消息解析失败:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] 连接关闭:', event.code, event.reason);
        setIsConnected(false);
        setIsConnecting(false);
        wsRef.current = null;
        onDisconnectRef.current?.();

        // 非手动关闭且未达重试上限，尝试重连
        if (!manualCloseRef.current && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          console.log(`[WebSocket] 尝试重连 (${reconnectCountRef.current}/${reconnectAttempts})...`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] 错误:', error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] 连接失败:', error);
      setIsConnecting(false);
    }
  }, [sessionId, reconnectAttempts, reconnectInterval]);

  // 断开连接
  const disconnect = useCallback(() => {
    manualCloseRef.current = true;
    clearReconnectTimeout();

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
  }, [clearReconnectTimeout]);

  // 发送消息
  const sendMessage = useCallback((message: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      console.log('[WebSocket] 发送消息:', message.type, message);
    } else {
      console.warn('[WebSocket] 连接未就绪，无法发送消息', {
        readyState: wsRef.current?.readyState,
        OPEN: WebSocket.OPEN
      });
    }
  }, []);

  // 发送 start 消息
  const sendStart = useCallback((payload: StartPayload) => {
    sendMessage({ type: 'start', payload });
  }, [sendMessage]);

  // 发送 continue 消息
  const sendContinue = useCallback((payload: ContinuePayload) => {
    sendMessage({ type: 'continue', payload });
  }, [sendMessage]);

  // 发送 cancel 消息
  const sendCancel = useCallback(() => {
    sendMessage({ type: 'cancel' });
  }, [sendMessage]);

  // 手动重连
  const reconnect = useCallback(() => {
    console.log('[WebSocket] 手动重连触发');

    // 先断开现有连接
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    // 重置状态
    manualCloseRef.current = false;
    reconnectCountRef.current = 0;
    clearReconnectTimeout();
    setIsConnected(false);
    setIsConnecting(false);

    // 重新连接
    if (sessionId) {
      // 使用 setTimeout 确保 state 更新完成后再连接
      setTimeout(() => {
        connect();
      }, 0);
    }
  }, [sessionId, connect, clearReconnectTimeout]);

  // 监听 sessionId 变化 - 只依赖 sessionId
  useEffect(() => {
    console.log('[WebSocket] useEffect 触发, sessionId:', sessionId, 'manualClose:', manualCloseRef.current);

    // 重置 manualClose 标志（React Strict Mode 双重渲染问题）
    manualCloseRef.current = false;

    if (sessionId) {
      // 使用 setTimeout 确保 state 更新完成后再连接
      const timer = setTimeout(() => {
        connect();
      }, 0);
      return () => {
        clearTimeout(timer);
        console.log('[WebSocket] 清理函数执行, sessionId:', sessionId);
        manualCloseRef.current = true;
        if (wsRef.current) {
          wsRef.current.close();
          wsRef.current = null;
        }
        setIsConnected(false);
        setIsConnecting(false);
      };
    }

    return () => {
      console.log('[WebSocket] 清理函数执行, sessionId:', sessionId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // 等待连接建立
  const whenConnected = useCallback((callback: () => void, timeout = 5000): Promise<boolean> => {
    return new Promise((resolve) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        callback();
        resolve(true);
        return;
      }

      const startTime = Date.now();
      const checkInterval = setInterval(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          clearInterval(checkInterval);
          callback();
          resolve(true);
        } else if (Date.now() - startTime > timeout) {
          clearInterval(checkInterval);
          console.warn('[WebSocket] 等待连接超时');
          resolve(false);
        }
      }, 100);
    });
  }, []);

  return {
    isConnected,
    isConnecting,
    sendStart,
    sendContinue,
    sendCancel,
    disconnect,
    reconnect,
    whenConnected,
  };
}
