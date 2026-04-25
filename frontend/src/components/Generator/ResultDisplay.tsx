/**
 * 结果展示组件
 *
 * 显示生成的文章内容
 */

import React from 'react';
import { Card, Typography, Tag, Space, Divider, Button } from 'antd';
import { CopyOutlined, DownloadOutlined } from '@ant-design/icons';
import type { CompletePayload } from '@/types';

const { Paragraph } = Typography;

interface ResultDisplayProps {
  result: CompletePayload | null;
}

export const ResultDisplay: React.FC<ResultDisplayProps> = ({ result }) => {
  if (!result) {
    return null;
  }

  const { finalText, outOfScopeWords = [], retryCount = 0, fallbackMode: isFallback = false } = result;

  // 复制到剪贴板
  const handleCopy = () => {
    if (finalText) {
      navigator.clipboard.writeText(finalText);
    }
  };

  // 下载文件
  const handleDownload = () => {
    if (finalText) {
      const blob = new Blob([finalText], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `vocabweaver-episode-${result.currentEpisode}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }
  };

  return (
    <Card
      title="生成结果"
      extra={
        <Space>
          <Button icon={<CopyOutlined />} onClick={handleCopy}>
            复制
          </Button>
          <Button icon={<DownloadOutlined />} onClick={handleDownload}>
            下载
          </Button>
        </Space>
      }
      className="w-full"
    >
      {/* 状态标签 */}
      <Space className="mb-4">
        {isFallback && (
          <Tag color="orange">兜底模式</Tag>
        )}
        {retryCount > 0 && (
          <Tag color="blue">重试 {retryCount} 次</Tag>
        )}
        {outOfScopeWords.length > 0 && (
          <Tag color="warning">含 {outOfScopeWords.length} 个超纲词</Tag>
        )}
      </Space>

      {/* 文章内容 */}
      {finalText ? (
        <div className="bg-gray-50 p-4 rounded-lg">
          <Paragraph
            style={{
              whiteSpace: 'pre-wrap',
              fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
              lineHeight: 1.8,
              fontSize: 16,
              margin: 0,
            }}
          >
            {finalText}
          </Paragraph>
        </div>
      ) : (
        <div className="text-center text-gray-400 py-8">
          无生成内容
        </div>
      )}

      {/* 超纲词列表 */}
      {outOfScopeWords.length > 0 && (
        <>
          <Divider>超纲词汇</Divider>
          <div className="flex flex-wrap gap-2">
            {outOfScopeWords.map((word, index) => (
              <Tag key={index} color="red">
                {word}
              </Tag>
            ))}
          </div>
        </>
      )}
    </Card>
  );
};
