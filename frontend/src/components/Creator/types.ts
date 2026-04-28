/**
 * Creator 组件类型定义
 */

export type ViewState = 'creation' | 'continuation' | 'completed';

export interface Chapter {
  episode: number;
  title: string;
  content: string;
  targetWords: string[];
  outOfScopeWords: string[];
  createdAt: string;
}

export interface CreatorProps {
  // 视图状态
  viewState: ViewState;

  // 创世视图数据
  style: string;
  totalEpisodes: number;
  initialPrompt: string;

  // 接龙视图数据
  currentEpisode: number;
  chapters: Chapter[];

  // 回调
  onStyleChange: (style: string) => void;
  onTotalEpisodesChange: (total: number) => void;
  onInitialPromptChange: (prompt: string) => void;
  onStartGeneration: (targetWords: string[]) => void;
  onContinueGeneration: (targetWords: string[]) => void;
  onReset: () => void;
  onExport: () => void;
}

// 风格选项
export const STYLE_OPTIONS = [
  { value: 'adventure', label: '冒险故事' },
  { value: 'scifi', label: '科幻小说' },
  { value: 'mystery', label: '悬疑推理' },
  { value: 'fairytale', label: '治愈童话' },
  { value: 'news', label: '新闻报道' },
  { value: 'exam_paper', label: '考试范文' },
  { value: 'webnovel', label: '网络小说' },
] as const;

export type StyleValue = typeof STYLE_OPTIONS[number]['value'];
