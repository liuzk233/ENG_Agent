/**
 * 章节卡片组件
 *
 * 直接显示完整内容（无打字机效果）
 */

import React from 'react';
import { Card, Tag, Typography } from 'antd';
import { WarningOutlined } from '@ant-design/icons';
import type { Chapter } from './types';

const { Text, Paragraph } = Typography;

interface ChapterCardProps {
  chapter: Chapter;
  isNew?: boolean; // 是否是新章节（保留参数但不使用打字机效果）
}

export const ChapterCard: React.FC<ChapterCardProps> = ({
  chapter,
  isNew = false,
}) => {
  const hasOutOfScope = chapter.outOfScopeWords.length > 0;
  const displayText = chapter.content || '';

  return (
    <Card
      className="mb-4 shadow-sm"
      title={
        <div className="flex items-center justify-between">
          <span className="text-lg font-medium">
            第 {chapter.episode} 章
            {isNew && <span className="ml-2 text-green-500">✓ 新生成</span>}
          </span>
          {hasOutOfScope && (
            <Tag color="warning" icon={<WarningOutlined />}>
              {chapter.outOfScopeWords.length} 个超纲词
            </Tag>
          )}
        </div>
      }
    >
      {/* 目标词汇 */}
      {chapter.targetWords.length > 0 && (
        <div className="mb-3">
          <Text type="secondary" className="text-xs">
            目标词汇：
          </Text>
          <div className="flex flex-wrap gap-1 mt-1">
            {chapter.targetWords.map((word) => (
              <Tag key={word} color="blue" className="text-xs">
                {word}
              </Tag>
            ))}
          </div>
        </div>
      )}

      {/* 文章内容 - 直接显示完整内容 */}
      <Paragraph
        className="text-gray-700 leading-relaxed whitespace-pre-wrap"
        style={{ marginBottom: 0, minHeight: '100px' }}
      >
        {displayText}
      </Paragraph>

      {/* 超纲词提示 */}
      {hasOutOfScope && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <Text type="secondary" className="text-xs">
            超纲词汇：
          </Text>
          <div className="flex flex-wrap gap-1 mt-1">
            {chapter.outOfScopeWords.map((word) => (
              <Tag key={word} color="orange" className="text-xs">
                {word}
              </Tag>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};
