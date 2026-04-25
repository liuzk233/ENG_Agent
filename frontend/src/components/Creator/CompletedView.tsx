/**
 * 视图三：完结视图
 *
 * 显示所有章节和完结提示
 */

import React from 'react';
import { Card, Button, Typography, Space } from 'antd';
import { DownloadOutlined, ReloadOutlined, TrophyOutlined } from '@ant-design/icons';
import { ChapterCard } from './ChapterCard';
import type { Chapter } from './types';

const { Text, Title } = Typography;

interface CompletedViewProps {
  chapters: Chapter[];
  onReset: () => void;
  onExport: () => void;
}

export const CompletedView: React.FC<CompletedViewProps> = ({
  chapters,
  onReset,
  onExport,
}) => {
  // 导出全文
  const handleExport = () => {
    const fullText = chapters
      .map((ch) => `【第 ${ch.episode} 章】\n\n${ch.content}`)
      .join('\n\n---\n\n');

    const blob = new Blob([fullText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `story_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);

    onExport?.();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 章节列表 */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        {chapters.map((chapter) => (
          <ChapterCard key={chapter.episode} chapter={chapter} />
        ))}

        {/* 完结提示框 */}
        <Card className="text-center bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-blue-200">
          <div className="py-6">
            <TrophyOutlined className="text-5xl text-yellow-500 mb-4" />
            <Title level={3} className="mb-2">
              🎉 The End
            </Title>
            <Text type="secondary" className="text-lg">
              故事已完结
            </Text>
            <Text type="secondary" className="block mt-1">
              共 {chapters.length} 章
            </Text>
          </div>

          <Space size="large" className="mt-4">
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleExport}
              size="large"
            >
              导出全文文本
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={onReset}
              size="large"
            >
              重新开始
            </Button>
          </Space>
        </Card>
      </div>
    </div>
  );
};
