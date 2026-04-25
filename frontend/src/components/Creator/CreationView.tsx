/**
 * 视图一：创世视图
 *
 * 用户设置故事风格、目标词汇、目标章节数
 */

import React, { useState } from 'react';
import { Card, Select, InputNumber, Button, Input, Typography, Space } from 'antd';
import { RocketOutlined } from '@ant-design/icons';
import { STYLE_OPTIONS } from './types';

const { TextArea } = Input;
const { Title, Text } = Typography;

interface CreationViewProps {
  style: string;
  totalEpisodes: number;
  onStyleChange: (style: string) => void;
  onTotalEpisodesChange: (total: number) => void;
  onStartGeneration: (targetWords: string[]) => void;
}

export const CreationView: React.FC<CreationViewProps> = ({
  style,
  totalEpisodes,
  onStyleChange,
  onTotalEpisodesChange,
  onStartGeneration,
}) => {
  const [targetWords, setTargetWords] = useState<string[]>([]);
  const [inputValue, setInputValue] = useState('');

  // 解析输入的词汇
  const parseWords = (value: string) => {
    const words = value
      .split(/[,，\n]/)
      .map((w) => w.trim())
      .filter((w) => w.length > 0);
    setTargetWords(words);
  };

  const handleStart = () => {
    if (targetWords.length > 0) {
      onStartGeneration(targetWords);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-blue-50 to-white p-8">
      <Card className="w-full max-w-2xl shadow-lg">
        <div className="text-center mb-8">
          <Title level={2} className="mb-2">
            开启一段新旅程
          </Title>
          <Text type="secondary">
            设置故事风格和目标词汇，开始创作你的专属故事
          </Text>
        </div>

        <Space direction="vertical" size="large" className="w-full">
          {/* 故事风格 */}
          <div>
            <label className="block mb-2 font-medium text-gray-700">
              故事风格
            </label>
            <Select
              value={style}
              onChange={onStyleChange}
              options={STYLE_OPTIONS.map((opt) => ({
                value: opt.value,
                label: opt.label,
              }))}
              className="w-full"
              size="large"
            />
          </div>

          {/* 目标词汇 */}
          <div>
            <label className="block mb-2 font-medium text-gray-700">
              第一章目标词汇
            </label>
            <TextArea
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                parseWords(e.target.value);
              }}
              placeholder="输入目标词汇，用逗号或换行分隔（例如：adventure, explore, discover）"
              rows={2}
              className="w-full"
            />
            {targetWords.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
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
          </div>

          {/* 目标章节数 */}
          <div>
            <label className="block mb-2 font-medium text-gray-700">
              目标章节数
            </label>
            <InputNumber
              value={totalEpisodes}
              onChange={(val) => onTotalEpisodesChange(val || 5)}
              min={1}
              max={20}
              className="w-full"
              size="large"
            />
          </div>

          {/* 开始按钮 */}
          <Button
            type="primary"
            size="large"
            icon={<RocketOutlined />}
            onClick={handleStart}
            disabled={targetWords.length === 0}
            block
            className="h-12 text-lg"
          >
            开始生成第一章
          </Button>
        </Space>
      </Card>
    </div>
  );
};
