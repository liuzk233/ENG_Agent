/**
 * 视图二：接龙视图
 *
 * 显示已生成的章节，并提供续写功能
 */

import React, { useState, useRef, useEffect } from 'react';
import { Card, Input, Button, Typography, Space, Progress, Spin } from 'antd';
import { PlusOutlined, LoadingOutlined } from '@ant-design/icons';
import { ChapterCard } from './ChapterCard';
import type { Chapter } from './types';

const { TextArea } = Input;
const { Text } = Typography;

interface ContinuationViewProps {
  currentEpisode: number;
  totalEpisodes: number;
  chapters: Chapter[];
  isGenerating: boolean;
  onContinueGeneration: (targetWords: string[]) => void;
}

export const ContinuationView: React.FC<ContinuationViewProps> = ({
  currentEpisode,
  totalEpisodes,
  chapters,
  isGenerating,
  onContinueGeneration,
}) => {
  const [inputValue, setInputValue] = useState('');
  const [targetWords, setTargetWords] = useState<string[]>([]);

  // 追踪新章节的 episode（用于触发打字机效果）
  const [newEpisode, setNewEpisode] = useState<number | null>(null);
  const prevChaptersRef = useRef<Chapter[]>([]);

  // 检测新章节添加
  useEffect(() => {
    if (chapters.length > prevChaptersRef.current.length) {
      // 有新章节添加
      const lastChapter = chapters[chapters.length - 1];
      if (lastChapter) {
        setNewEpisode(lastChapter.episode);
      }
    }
    prevChaptersRef.current = chapters;
  }, [chapters]);

  // 解析输入的词汇
  const parseWords = (value: string) => {
    const words = value
      .split(/[,，\n]/)
      .map((w) => w.trim())
      .filter((w) => w.length > 0);
    setTargetWords(words);
  };

  const handleContinue = () => {
    if (targetWords.length > 0) {
      onContinueGeneration(targetWords);
      setInputValue('');
      setTargetWords([]);
    }
  };

  const nextEpisode = currentEpisode + 1;
  const isLastChapter = currentEpisode >= totalEpisodes;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* 顶部进度区域 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto">
          <div className="flex items-center justify-between mb-2">
            <Text strong>连载进度</Text>
            <Text type="secondary">
              {currentEpisode} / {totalEpisodes} 章
            </Text>
          </div>
          <Progress
            percent={Math.round((currentEpisode / totalEpisodes) * 100)}
            showInfo={false}
            strokeColor="#1890ff"
          />
        </div>
      </div>

      {/* 中部内容区域 */}
      <div className="flex-1 overflow-y-auto px-6 py-8">
        <div className="max-w-4xl mx-auto">
          {/* 章节列表 - 带打字机效果 */}
          {chapters.map((chapter) => (
            <ChapterCard
              key={chapter.episode}
              chapter={chapter}
              isNew={chapter.episode === newEpisode}
            />
          ))}

          {/* 生成中状态 */}
          {isGenerating && (
            <Card className="mb-4">
              <div className="flex items-center justify-center">
                <Spin indicator={<LoadingOutlined spin />} />
                <Text className="ml-3">正在生成第 {nextEpisode} 章...</Text>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* 底部操作区域 - 只有未完结且未在生成时显示 */}
      {!isLastChapter && !isGenerating && (
        <div className="bg-white border-t border-gray-200 px-6 py-4 sticky bottom-0">
          <div className="max-w-4xl mx-auto">
            <Card size="small" className="bg-gray-50">
              <Space direction="vertical" size="middle" className="w-full">
                <Text type="secondary">
                  第 {currentEpisode} 章结束。接下来的情节将围绕什么词汇展开？
                </Text>

                <TextArea
                  value={inputValue}
                  onChange={(e) => {
                    setInputValue(e.target.value);
                    parseWords(e.target.value);
                  }}
                  placeholder="输入下一章目标词汇，用逗号分隔"
                  rows={2}
                  disabled={isGenerating}
                />

                {targetWords.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {targetWords.map((word) => (
                      <span
                        key={word}
                        className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-sm"
                      >
                        {word}
                      </span>
                    ))}
                  </div>
                )}

                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleContinue}
                  disabled={targetWords.length === 0 || isGenerating}
                  size="large"
                  block
                >
                  生成第 {nextEpisode} 章
                </Button>
              </Space>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};
