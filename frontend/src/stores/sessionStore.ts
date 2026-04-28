/**
 * Zustand 状态管理
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type {
  Session,
  GenerationState,
  NodeState,
  NodeStatus,
  CompletePayload,
} from '@/types';

// ============================================================
// 三视图状态类型
// ============================================================

export type ViewState = 'creation' | 'continuation' | 'completed';

export interface Chapter {
  episode: number;
  title: string;
  content: string;
  targetWords: string[];
  outOfScopeWords: string[];
  createdAt: string;
}

export interface CreatorState {
  viewState: ViewState;
  style: string;
  totalEpisodes: number;
  currentEpisode: number;
  chapters: Chapter[];
  initialPrompt: string;
}

// ============================================================
// 会话 Store
// ============================================================

interface SessionStore {
  // 用户信息
  userId: string;
  setUserId: (id: string) => void;

  // 当前会话
  currentSession: Session | null;
  setCurrentSession: (session: Session | null) => void;

  // 历史会话
  sessions: Session[];
  addSession: (session: Session) => void;
  clearSessions: () => void;

  // 三视图状态
  creator: CreatorState;
  setViewState: (viewState: ViewState) => void;
  setStyle: (style: string) => void;
  setTotalEpisodes: (total: number) => void;
  setCurrentEpisode: (episode: number) => void;
  addChapter: (chapter: Chapter) => void;
  setInitialPrompt: (prompt: string) => void;
  resetCreator: () => void;
}

const initialCreatorState: CreatorState = {
  viewState: 'creation',
  style: 'adventure',
  totalEpisodes: 5,
  currentEpisode: 0,
  chapters: [],
  initialPrompt: '',
};

export const useSessionStore = create<SessionStore>()(
  persist(
    (set) => ({
      userId: 'anonymous',  // 使用固定 userId 以便加载历史会话
      setUserId: (id) => set({ userId: id }),

      currentSession: null,
      setCurrentSession: (session) => set({ currentSession: session }),

      sessions: [],
      addSession: (session) =>
        set((state) => {
          // 检查是否已存在相同 sessionId
          const existingIndex = state.sessions.findIndex(
            (s) => s.sessionId === session.sessionId
          );

          if (existingIndex >= 0) {
            // 更新已存在的会话
            const updated = [...state.sessions];
            updated[existingIndex] = {
              ...updated[existingIndex],
              ...session,
            };
            return { sessions: updated };
          }

          // 添加新会话
          return {
            sessions: [session, ...state.sessions].slice(0, 20), // 保留最近 20 个
          };
        }),
      clearSessions: () => set({ sessions: [] }),

      // 三视图状态
      creator: initialCreatorState,
      setViewState: (viewState) =>
        set((state) => ({
          creator: { ...state.creator, viewState },
        })),
      setStyle: (style) =>
        set((state) => ({
          creator: { ...state.creator, style },
        })),
      setTotalEpisodes: (totalEpisodes) =>
        set((state) => ({
          creator: { ...state.creator, totalEpisodes },
        })),
      setCurrentEpisode: (currentEpisode) =>
        set((state) => ({
          creator: { ...state.creator, currentEpisode },
        })),
      addChapter: (chapter) =>
        set((state) => ({
          creator: {
            ...state.creator,
            chapters: [...state.creator.chapters, chapter],
            currentEpisode: chapter.episode,
          },
        })),
      setInitialPrompt: (initialPrompt) =>
        set((state) => ({
          creator: { ...state.creator, initialPrompt },
        })),
      resetCreator: () =>
        set((state) => ({
          creator: { ...initialCreatorState, style: state.creator.style },
        })),
    }),
    {
      name: 'vocabweaver-session',
      partialize: (state) => ({
        userId: state.userId,
        sessions: state.sessions,
      }),
    }
  )
);

// ============================================================
// 生成状态 Store
// ============================================================

interface GenerationStore {
  // 生成状态
  state: GenerationState;

  // Actions
  startGeneration: (totalEpisodes: number) => void;
  updateNode: (node: string, status: NodeStatus, data?: Partial<NodeState>) => void;
  setCurrentEpisode: (episode: number) => void;
  setTotalEpisodes: (total: number) => void;
  setResult: (result: CompletePayload) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialGenerationState: GenerationState = {
  isGenerating: false,
  currentNode: null,
  nodes: {},
  currentEpisode: 1,
  totalEpisodes: 1,
  result: null,
  error: null,
};

export const useGenerationStore = create<GenerationStore>((set) => ({
  state: initialGenerationState,

  startGeneration: (totalEpisodes) =>
    set({
      state: {
        ...initialGenerationState,
        isGenerating: true,
        totalEpisodes,
        nodes: {
          initialize: { status: 'pending' },
          planner: { status: 'pending' },
          writer: { status: 'pending' },
          reviewer: { status: 'pending' },
          memory: { status: 'pending' },
        },
      },
    }),

  updateNode: (node, status, data) =>
    set((store) => ({
      state: {
        ...store.state,
        currentNode: status === 'running' ? node : store.state.currentNode,
        nodes: {
          ...store.state.nodes,
          [node]: {
            ...store.state.nodes[node],
            status,
            ...data,
          },
        },
      },
    })),

  setCurrentEpisode: (episode) =>
    set((store) => ({
      state: {
        ...store.state,
        currentEpisode: episode,
      },
    })),

  setTotalEpisodes: (total) =>
    set((store) => ({
      state: {
        ...store.state,
        totalEpisodes: total,
      },
    })),

  setResult: (result) =>
    set((store) => ({
      state: {
        ...store.state,
        isGenerating: false,
        result,
      },
    })),

  setError: (error) =>
    set((store) => ({
      state: {
        ...store.state,
        isGenerating: false,
        error,
      },
    })),

  reset: () => set({ state: initialGenerationState }),
}));
