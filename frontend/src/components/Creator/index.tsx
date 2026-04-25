/**
 * Creator 主组件
 *
 * 三视图状态机：创世 → 接龙 → 完结
 */

import React, { useEffect, useRef } from 'react';
import { useSessionStore, useGenerationStore } from '@/stores/sessionStore';
import { CreationView } from './CreationView';
import { ContinuationView } from './ContinuationView';
import { CompletedView } from './CompletedView';
import { ProgressPanel } from '../Generator/ProgressPanel';
import type { Chapter } from './types';

interface CreatorProps {
  // WebSocket 相关
  isConnected: boolean;
  isGenerating: boolean;
  sessionId: string | null;

  // 操作
  startGeneration: (targetWords: string[], style?: string, totalEpisodes?: number) => void;
  continueGeneration: (targetWords: string[]) => void;
  resetGeneration: () => void;

  // 生成结果
  result: {
    sessionId?: string;
    currentEpisode?: number;
    finalText?: string;
    outOfScopeWords?: string[];
  } | null;
}

export const Creator: React.FC<CreatorProps> = ({
  isGenerating,
  startGeneration,
  continueGeneration,
  resetGeneration,
  result,
}) => {
  const {
    creator,
    setViewState,
    setStyle,
    setTotalEpisodes,
    addChapter,
    resetCreator,
  } = useSessionStore();

  const { state: generationState } = useGenerationStore();

  // 用于防止重复添加章节
  const lastAddedEpisodeRef = useRef<number | null>(null);

  // 当生成完成时，添加章节并检查是否需要切换视图
  useEffect(() => {
    if (result && result.finalText && !isGenerating) {
      const episodeNum = result.currentEpisode || 1;

      // 防止重复添加同一章节
      if (lastAddedEpisodeRef.current === episodeNum) {
        console.log('[Creator] 跳过重复添加章节:', episodeNum);
        return;
      }

      // 检查是否已存在该章节
      const existingChapter = creator.chapters.find((ch) => ch.episode === episodeNum);
      if (existingChapter) {
        console.log('[Creator] 章节已存在:', episodeNum);
        return;
      }

      console.log('[Creator] 添加新章节:', episodeNum);

      // 添加新章节
      const newChapter: Chapter = {
        episode: episodeNum,
        title: `第 ${episodeNum} 章`,
        content: result.finalText,
        targetWords: [],
        outOfScopeWords: result.outOfScopeWords || [],
        createdAt: new Date().toISOString(),
      };

      addChapter(newChapter);
      lastAddedEpisodeRef.current = episodeNum;

      // 检查是否完成所有章节
      if (episodeNum >= creator.totalEpisodes) {
        setViewState('completed');
      } else {
        setViewState('continuation');
      }
    }
  }, [result, isGenerating]);

  // 重置时清空防重复标记
  useEffect(() => {
    if (creator.viewState === 'creation') {
      lastAddedEpisodeRef.current = null;
    }
  }, [creator.viewState]);

  // 处理开始生成
  const handleStartGeneration = (targetWords: string[]) => {
    startGeneration(targetWords, creator.style, creator.totalEpisodes);
    setViewState('continuation');
  };

  // 处理继续生成
  const handleContinueGeneration = (targetWords: string[]) => {
    continueGeneration(targetWords);
  };

  // 处理重置
  const handleReset = () => {
    resetCreator();
    resetGeneration();
    lastAddedEpisodeRef.current = null;
  };

  // 处理导出
  const handleExport = () => {
    console.log('Export triggered');
  };

  // 如果正在生成，显示进度面板
  if (isGenerating && generationState.nodes) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto">
          <ProgressPanel
            nodes={generationState.nodes}
            currentEpisode={generationState.currentEpisode}
            totalEpisodes={generationState.totalEpisodes}
          />
        </div>
      </div>
    );
  }

  // 根据视图状态渲染对应组件
  switch (creator.viewState) {
    case 'creation':
      return (
        <CreationView
          style={creator.style}
          totalEpisodes={creator.totalEpisodes}
          onStyleChange={setStyle}
          onTotalEpisodesChange={setTotalEpisodes}
          onStartGeneration={handleStartGeneration}
        />
      );

    case 'continuation':
      return (
        <ContinuationView
          currentEpisode={creator.currentEpisode}
          totalEpisodes={creator.totalEpisodes}
          chapters={creator.chapters}
          isGenerating={isGenerating}
          onContinueGeneration={handleContinueGeneration}
        />
      );

    case 'completed':
      return (
        <CompletedView
          chapters={creator.chapters}
          onReset={handleReset}
          onExport={handleExport}
        />
      );

    default:
      return null;
  }
};

export { CreationView } from './CreationView';
export { ContinuationView } from './ContinuationView';
export { CompletedView } from './CompletedView';
export { ChapterCard } from './ChapterCard';
export type { Chapter, ViewState } from './types';
