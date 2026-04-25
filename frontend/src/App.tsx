/**
 * 主应用组件
 *
 * 使用三视图状态机：创世 → 接龙 → 完结
 */

import React, { useCallback } from 'react';
import { message } from 'antd';

import { Header, Sidebar } from '@/components/Layout';
import { Creator } from '@/components/Creator';
import { useGeneration } from '@/hooks/useGeneration';
import { useSessionStore } from '@/stores/sessionStore';
import type { Session, Chapter } from '@/types';

const App: React.FC = () => {
  const { setCurrentSession, setViewState, setTotalEpisodes, addChapter, resetCreator } = useSessionStore();

  // 生成流程
  const {
    isGenerating,
    isConnected,
    sessionId,
    generationState,
    startGeneration,
    continueGeneration,
    resetGeneration,
  } = useGeneration();

  // 处理历史会话选择
  const handleSelectSession = useCallback(async (session: Session) => {
    try {
      // 0. 重置 creator 状态，避免混入旧数据
      resetCreator();

      // 1. 从后端获取完整会话状态
      const response = await fetch(`/api/sessions/${session.sessionId}`);

      if (!response.ok) {
        throw new Error('会话不存在');
      }

      const data = await response.json();

      // 2. 更新当前会话
      setCurrentSession(data);

      // 3. 获取已生成的章节
      const episodesResponse = await fetch(`/api/sessions/${session.sessionId}/episodes`);
      const episodes = episodesResponse.ok ? await episodesResponse.json() : [];

      // 4. 恢复状态
      setTotalEpisodes(data.total_episodes);

      // 5. 添加已有章节
      if (episodes && episodes.length > 0) {
        episodes.forEach((ep: any) => {
          const chapter: Chapter = {
            episode: ep.episode_num,
            title: `第 ${ep.episode_num} 章`,
            content: ep.final_text || '',
            targetWords: ep.target_words || [],
            outOfScopeWords: ep.out_of_scope_words || [],
            createdAt: ep.created_at || new Date().toISOString(),
          };
          addChapter(chapter);
        });
      }

      // 6. 判断视图状态
      if (data.current_episode >= data.total_episodes) {
        setViewState('completed');
      } else {
        setViewState('continuation');
      }

      message.success('会话已恢复');
    } catch (error) {
      console.error('恢复会话失败:', error);
      message.error('恢复会话失败，请重试');
    }
  }, [setCurrentSession, setTotalEpisodes, addChapter, setViewState]);

  // 处理新建对话
  const handleNewChat = useCallback(() => {
    resetCreator();
    resetGeneration();
    setCurrentSession(null);
  }, [resetCreator, resetGeneration, setCurrentSession]);

  return (
    <div className="min-h-screen bg-[#FFFFFF] font-[Outfit,sans-serif] flex">
      {/* 侧边栏 */}
      <Sidebar
        onSelectSession={handleSelectSession}
        onNewChat={handleNewChat}
      />

      {/* 主内容区域 */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* 头部 */}
        <Header />

        {/* 内容 */}
        <main className="flex-1 bg-[#FFFFFF]">
          <Creator
            isConnected={isConnected}
            isGenerating={isGenerating}
            sessionId={sessionId}
            startGeneration={startGeneration}
            continueGeneration={continueGeneration}
            resetGeneration={resetGeneration}
            result={generationState.result}
          />

          {/* 错误信息 */}
          {generationState.error && (
            <div className="fixed bottom-4 right-4 max-w-md">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 shadow-lg">
                <p className="text-red-600">{generationState.error}</p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
