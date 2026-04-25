/**
 * 侧边栏组件
 *
 * 参考 ChatGPT 风格设计，简洁精致
 */

import React, { useEffect, useState } from 'react';
import { PlusOutlined, MessageOutlined, MenuFoldOutlined } from '@ant-design/icons';
import { useSessionStore } from '@/stores/sessionStore';
import type { Session } from '@/types';

interface SidebarProps {
  onSelectSession?: (session: Session) => void;
  onNewChat?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ onSelectSession, onNewChat }) => {
  const { sessions, userId } = useSessionStore();
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // 从后端加载历史会话列表
  useEffect(() => {
    const loadSessions = async () => {
      if (!userId) return;

      setLoading(true);
      try {
        const response = await fetch(`/api/users/${userId}/sessions?limit=10`);
        if (response.ok) {
          const data = await response.json();
          const backendSessions: Session[] = (data.sessions || []).map((s: any) => ({
            sessionId: s.session_id,
            userId: s.user_id,
            status: s.status,
            currentEpisode: s.current_episode,
            totalEpisodes: s.total_episodes,
            style: s.style,
            createdAt: s.created_at || new Date().toISOString(),
          }));
          useSessionStore.setState({ sessions: backendSessions });
        }
      } catch (error) {
        console.error('加载历史会话失败:', error);
      } finally {
        setLoading(false);
      }
    };

    loadSessions();
  }, [userId]);

  // 格式化日期
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return '今天';
    if (diffDays === 1) return '昨天';
    if (diffDays < 7) return `${diffDays}天前`;
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
  };

  // 按日期分组会话
  const groupedSessions = sessions.reduce((groups, session) => {
    const date = formatDate(session.createdAt);
    if (!groups[date]) groups[date] = [];
    groups[date].push(session);
    return groups;
  }, {} as Record<string, Session[]>);

  if (collapsed) {
    return (
      <div className="w-[60px] h-screen bg-[#FAFAFA] border-r border-[#E5E5E5] flex flex-col items-center py-4 transition-all duration-300">
        <button
          onClick={() => setCollapsed(false)}
          className="w-10 h-10 rounded-lg hover:bg-[#F0F0F0] flex items-center justify-center transition-colors focus:outline-none"
          title="展开侧边栏"
        >
          <MessageOutlined className="text-lg text-[#6B6B6B]" />
        </button>
      </div>
    );
  }

  return (
    <div className="w-[280px] h-screen bg-[#FAFAFA] border-r border-[#E5E5E5] flex flex-col transition-all duration-300 font-[Outfit,sans-serif]">
      {/* 顶部：新聊天按钮 + 折叠按钮 */}
      <div className="p-3 flex items-center gap-2">
        <button
          onClick={onNewChat}
          className="flex-1 h-11 rounded-lg border border-[#E5E5E5] bg-white hover:bg-[#F5F5F5] flex items-center justify-center gap-2 transition-all duration-200 text-[#1A1A1A] text-sm font-medium focus:outline-none"
        >
          <PlusOutlined className="text-sm" />
          <span>新对话</span>
        </button>
        <button
          onClick={() => setCollapsed(true)}
          className="w-11 h-11 rounded-lg hover:bg-[#F0F0F0] flex items-center justify-center transition-colors focus:outline-none"
          title="收起侧边栏"
        >
          <MenuFoldOutlined className="text-lg text-[#6B6B6B]" />
        </button>
      </div>

      {/* 中间：历史会话列表 */}
      <div className="flex-1 overflow-y-auto px-2">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="w-5 h-5 border-2 border-[#E5E5E5] border-t-[#10A37F] rounded-full animate-spin" />
          </div>
        ) : Object.keys(groupedSessions).length === 0 ? (
          <div className="text-center py-12 text-[#9B9B9B] text-sm">
            暂无历史对话
          </div>
        ) : (
          Object.entries(groupedSessions).map(([date, dateSessions]) => (
            <div key={date} className="mb-4">
              <div className="px-3 py-2 text-xs text-[#9B9B9B] font-medium">
                {date}
              </div>
              {dateSessions.map((session) => (
                <div
                  key={session.sessionId}
                  onClick={() => onSelectSession?.(session)}
                  className="group px-3 py-2.5 rounded-lg hover:bg-[#F0F0F0] cursor-pointer transition-colors duration-150"
                >
                  <div className="flex items-center gap-2">
                    <MessageOutlined className="text-sm text-[#9B9B9B]" />
                    <span className="text-sm text-[#1A1A1A] truncate flex-1">
                      第 {session.currentEpisode}/{session.totalEpisodes} 章
                    </span>
                    {session.status === 'completed' && (
                      <span className="text-xs text-[#10A37F] bg-[#E8F5F0] px-1.5 py-0.5 rounded">
                        完成
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
