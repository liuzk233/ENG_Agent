/**
 * 生成流程 Hook
 *
 * 整合 WebSocket 和状态管理
 */

import { useCallback, useState, useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { useGenerationStore, useSessionStore } from '@/stores/sessionStore';
import type { ServerMessage, StartPayload, ContinuePayload, NodeEndPayload, CompletePayload, GenerationState } from '@/types';

interface UseGenerationOptions {
  totalEpisodes?: number;
  style?: string;
}

interface UseGenerationReturn {
  // 状态
  isGenerating: boolean;
  isConnected: boolean;
  sessionId: string | null;
  generationState: GenerationState;

  // 操作
  startGeneration: (targetWords: string[], style?: string, totalEpisodes?: number) => void;
  continueGeneration: (targetWords: string[]) => void;
  cancelGeneration: () => void;
  resetGeneration: () => void;
  restoreSession: (sessionId: string, totalEpisodes: number) => void;
}

export function useGeneration(options: UseGenerationOptions = {}): UseGenerationReturn {
  const [sessionId, setSessionId] = useState<string | null>(null);

  // 待发送的消息队列（等待连接建立后发送）
  const pendingMessageRef = useRef<{
    type: 'start' | 'continue';
    payload: StartPayload | ContinuePayload;
  } | null>(null);

  // 用于追踪是否已发送，避免重复发送
  const messageSentRef = useRef(false);

  // 追踪当前是否是新会话模式（用于决定 complete 时是否添加新会话）
  const isNewSessionRef = useRef(false);

  const { userId, setCurrentSession, addSession } = useSessionStore();
  const { state, startGeneration: start, updateNode, setTotalEpisodes, setResult, setError, reset } = useGenerationStore();

  // 处理 WebSocket 消息
  const handleWebSocketMessage = useCallback((message: ServerMessage) => {
    console.log('[Generation] 收到消息:', message.type);

    switch (message.type) {
      case 'node_start':
        if (message.payload && 'node' in message.payload) {
          const node = (message.payload as { node: string }).node;
          updateNode(node, 'running');
        }
        break;

      case 'node_end':
        if (message.payload && 'node' in message.payload) {
          const payload = message.payload as NodeEndPayload;
          // 后端使用 snake_case，前端使用 camelCase
          // 使用类型断言处理 snake_case 字段
          const rawData = (payload.data || {}) as Record<string, unknown>;
          const node = payload.node;
          const status = payload.status;
          updateNode(node, status === 'success' ? 'success' : 'failed', {
            retryCount: rawData.retry_count as number | undefined,
            outOfScopeWords: rawData.out_of_scope_words as string[] | undefined,
          });
        }
        break;

      case 'progress':
        if (message.payload && 'currentEpisode' in message.payload) {
          const payload = message.payload as { currentEpisode?: number; totalEpisodes?: number; total_episodes?: number };
          // 后端可能使用 snake_case 或 camelCase
          reset();
          start(payload.totalEpisodes || payload.total_episodes || 1);
        }
        break;

      case 'complete':
        if (message.payload && ('sessionId' in message.payload || 'session_id' in message.payload)) {
          const rawPayload = message.payload as Record<string, unknown>;
          // 后端使用 snake_case，转换为 camelCase
          const payload: CompletePayload = {
            sessionId: (rawPayload.session_id || rawPayload.sessionId) as string,
            currentEpisode: (rawPayload.current_episode || rawPayload.currentEpisode) as number,
            finalText: (rawPayload.final_text || rawPayload.finalText) as string | undefined,
            outOfScopeWords: (rawPayload.out_of_scope_words || rawPayload.outOfScopeWords || []) as string[],
            retryCount: (rawPayload.retry_count ?? rawPayload.retryCount ?? 0) as number,
            fallbackMode: (rawPayload.fallback_mode ?? rawPayload.fallbackMode ?? false) as boolean,
          };

          // 更新 totalEpisodes（后端新增字段）
          const totalEpisodesFromBackend = rawPayload.total_episodes as number | undefined;
          if (totalEpisodesFromBackend && totalEpisodesFromBackend !== state.totalEpisodes) {
            // 使用后端返回的 totalEpisodes
            start(totalEpisodesFromBackend);
          }

          setResult(payload);

          // 保存会话
          const session = {
            sessionId: payload.sessionId,
            userId,
            status: 'active' as const,
            currentEpisode: payload.currentEpisode,
            totalEpisodes: totalEpisodesFromBackend || state.totalEpisodes,
            style: options.style || 'adventure',
            createdAt: new Date().toISOString(),
          };
          setCurrentSession(session);
          addSession(session);
        }
        break;

      case 'error':
        if (message.payload && 'message' in message.payload) {
          const payload = message.payload as { message: string };
          setError(payload.message);
        }
        break;

      case 'cancelled':
        reset();
        break;
    }
  }, [updateNode, setResult, setError, reset, start, userId, setCurrentSession, addSession, state.totalEpisodes, options.style]);

  // WebSocket 连接
  const { isConnected, sendStart, sendContinue, sendCancel, reconnect } = useWebSocket({
    sessionId,
    onMessage: handleWebSocketMessage,
  });

  // 当连接建立后，发送待发送的消息
  useEffect(() => {
    console.log('[Generation] isConnected 变化:', isConnected, 'pending:', !!pendingMessageRef.current, 'sent:', messageSentRef.current);

    // 如果已连接且有待发送消息且未发送
    if (isConnected && pendingMessageRef.current && !messageSentRef.current) {
      const pending = pendingMessageRef.current;
      messageSentRef.current = true; // 标记已发送

      console.log('[Generation] 连接已建立，发送待发消息:', pending.type, pending.payload);

      if (pending.type === 'start') {
        sendStart(pending.payload as StartPayload);
      } else if (pending.type === 'continue') {
        sendContinue(pending.payload as ContinuePayload);
      }
    } else if (isConnected && !pendingMessageRef.current) {
      // 连接已建立但没有待发送消息，可能是重连场景
      console.log('[Generation] 连接已建立，但无待发送消息');
    }
    // 只依赖 isConnected，sendStart/sendContinue 是稳定的
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isConnected]);

  // 额外的 effect：当 pendingMessageRef 变化时检查是否可以发送
  // 这处理了 pending 消息在连接之后设置的情况
  useEffect(() => {
    if (isConnected && pendingMessageRef.current && !messageSentRef.current) {
      const pending = pendingMessageRef.current;
      messageSentRef.current = true;

      console.log('[Generation] pending 消息变化，立即发送:', pending.type);

      if (pending.type === 'start') {
        sendStart(pending.payload as StartPayload);
      } else if (pending.type === 'continue') {
        sendContinue(pending.payload as ContinuePayload);
      }
    }
  }); // 无依赖，每次渲染都检查

  // 开始生成
  const startGeneration = useCallback((targetWords: string[], style?: string, totalEpisodes?: number) => {
    const episodes = totalEpisodes || options.totalEpisodes || 1;
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).slice(2)}`;

    // 设置待发送消息
    const payload: StartPayload = {
      userId,
      targetWords,
      style: style || options.style || 'adventure',
      totalEpisodes: episodes,
    };

    // 先设置 pending 消息
    pendingMessageRef.current = { type: 'start', payload };
    messageSentRef.current = false; // 重置发送标记
    isNewSessionRef.current = true; // 标记为新会话

    console.log('[Generation] 设置 sessionId，等待连接:', newSessionId);
    console.log('[Generation] 待发送消息:', payload);

    // 重置状态并设置新 sessionId（触发 WebSocket 连接）
    start(episodes);
    setSessionId(newSessionId);
  }, [userId, options.totalEpisodes, options.style, start]);

  // 续写
  const continueGeneration = useCallback((targetWords: string[]) => {
    const payload: ContinuePayload = {
      userId,
      targetWords,
    };

    // 设置待发送消息
    pendingMessageRef.current = { type: 'continue', payload };
    messageSentRef.current = false;
    isNewSessionRef.current = false; // 标记为续写模式

    console.log('[Generation] 续写请求, isConnected:', isConnected);

    if (isConnected) {
      // 连接正常，直接发送
      sendContinue(payload);
      messageSentRef.current = true;
    } else {
      // 连接断开，触发重连
      console.log('[Generation] 连接断开，触发重连');
      reconnect();
      // 消息会在 useEffect 中连接建立后发送
    }
  }, [isConnected, sendContinue, reconnect, userId]);

  // 取消
  const cancelGeneration = useCallback(() => {
    sendCancel();
    reset();
    pendingMessageRef.current = null;
    messageSentRef.current = false;
  }, [sendCancel, reset]);

  // 重置
  const resetGeneration = useCallback(() => {
    reset();
    setSessionId(null);
    pendingMessageRef.current = null;
    messageSentRef.current = false;
  }, [reset]);

  // 恢复历史会话（用于续写）
  const restoreSession = useCallback((existingSessionId: string, totalEpisodes: number) => {
    console.log('[Generation] 恢复会话:', existingSessionId, 'totalEpisodes:', totalEpisodes);

    // 重置状态（但不进入生成状态）
    reset();
    setTotalEpisodes(totalEpisodes);
    pendingMessageRef.current = null;
    messageSentRef.current = false;
    isNewSessionRef.current = false;

    // 设置 sessionId（触发 WebSocket 连接）
    setSessionId(existingSessionId);
  }, [reset, setTotalEpisodes]);

  return {
    isGenerating: state.isGenerating,
    isConnected,
    sessionId,
    generationState: state,
    startGeneration,
    continueGeneration,
    cancelGeneration,
    resetGeneration,
    restoreSession,
  };
}
