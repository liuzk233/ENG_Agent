/**
 * TypeScript 类型定义
 */

// ============================================================
// 会话类型
// ============================================================

export interface Session {
  sessionId: string;
  userId: string;
  status: 'active' | 'completed' | 'cancelled';
  currentEpisode: number;
  totalEpisodes: number;
  style: string;
  title?: string;
  createdAt: string;
}

export interface Episode {
  episodeNum: number;
  finalText: string | null;
  targetWords: string[];
  outOfScopeWords: string[];
  retryCount: number;
  fallbackMode: boolean;
}

export interface Chapter {
  episode: number;
  title: string;
  content: string;
  targetWords: string[];
  outOfScopeWords: string[];
  createdAt: string;
}

// ============================================================
// 生成请求
// ============================================================

export interface GenerateRequest {
  userId: string;
  totalEpisodes: number;
  targetWords: string[];
  style: string;
}

export interface ContinueRequest {
  userId: string;
  sessionId: string;
  targetWords: string[];
}

// ============================================================
// WebSocket 消息
// ============================================================

export type ClientMessageType = 'start' | 'continue' | 'cancel';

export interface ClientMessage {
  type: ClientMessageType;
  payload?: StartPayload | ContinuePayload;
}

export interface StartPayload {
  userId?: string;
  targetWords: string[];
  style?: string;
  totalEpisodes?: number;
}

export interface ContinuePayload {
  userId?: string;
  targetWords: string[];
}

// ============================================================
// 服务端消息
// ============================================================

export type ServerMessageType = 'node_start' | 'node_end' | 'progress' | 'error' | 'complete' | 'cancelled';

export interface ServerMessage {
  type: ServerMessageType;
  payload: NodeEndPayload | ProgressPayload | ErrorPayload | CompletePayload;
}

export interface NodeEndPayload {
  node: string;
  nodeLabel?: string;
  status: 'success' | 'failed';
  data?: {
    retryCount?: number;
    isValid?: boolean;
    outOfScopeWords?: string[];
    draftText?: string;
    currentEpisode?: number;
  };
}

export interface ProgressPayload {
  currentEpisode: number;
  totalEpisodes: number;
  node: string;
}

export interface ErrorPayload {
  message: string;
  node?: string;
}

export interface CompletePayload {
  sessionId: string;
  currentEpisode: number;
  finalText?: string;
  outOfScopeWords?: string[];
  retryCount?: number;
  fallbackMode?: boolean;
}

// ============================================================
// UI 状态
// ============================================================

export type NodeStatus = 'pending' | 'running' | 'success' | 'failed';

export interface NodeState {
  status: NodeStatus;
  retryCount?: number;
  outOfScopeWords?: string[];
}

export interface GenerationState {
  isGenerating: boolean;
  currentNode: string | null;
  nodes: Record<string, NodeState>;
  currentEpisode: number;
  totalEpisodes: number;
  result: CompletePayload | null;
  error: string | null;
}

// ============================================================
// 风格选项
// ============================================================

export const STYLE_OPTIONS = [
  { value: 'adventure', label: '冒险故事' },
  { value: 'scifi', label: '科幻小说' },
  { value: 'mystery', label: '悬疑推理' },
  { value: 'news', label: '新闻报道' },
  { value: 'exam_paper', label: '考试范文' },
] as const;

export type StyleValue = typeof STYLE_OPTIONS[number]['value'];
