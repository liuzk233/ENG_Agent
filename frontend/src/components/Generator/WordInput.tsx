/**
 * 词汇输入组件
 */

import React, { useState } from 'react';
import { Input, Button, Tag, Space } from 'antd';
import { PlusOutlined, CloseOutlined } from '@ant-design/icons';

const { TextArea } = Input;

interface WordInputProps {
  value: string[];
  onChange: (words: string[]) => void;
  placeholder?: string;
}

export const WordInput: React.FC<WordInputProps> = ({
  value,
  onChange,
  placeholder = '输入单词，按回车或逗号分隔',
}) => {
  const [inputValue, setInputValue] = useState('');

  // 解析输入
  const parseWords = (text: string): string[] => {
    return text
      .split(/[,\n，]/)
      .map((w) => w.trim().toLowerCase())
      .filter((w) => w.length > 0 && !value.includes(w));
  };

  // 添加单词
  const handleAdd = () => {
    const newWords = parseWords(inputValue);
    if (newWords.length > 0) {
      onChange([...value, ...newWords]);
      setInputValue('');
    }
  };

  // 回车添加
  const handlePressEnter = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAdd();
    }
  };

  // 移除单词
  const handleRemove = (word: string) => {
    onChange(value.filter((w) => w !== word));
  };

  // 清空所有
  const handleClear = () => {
    onChange([]);
  };

  return (
    <div className="w-full">
      {/* 已选单词 */}
      {value.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1">
          {value.map((word) => (
            <Tag
              key={word}
              closable
              onClose={() => handleRemove(word)}
              closeIcon={<CloseOutlined style={{ fontSize: 10 }} />}
              color="blue"
            >
              {word}
            </Tag>
          ))}
          <Button
            type="link"
            size="small"
            onClick={handleClear}
            className="text-gray-400"
          >
            清空
          </Button>
        </div>
      )}

      {/* 输入框 */}
      <Space.Compact className="w-full">
        <TextArea
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handlePressEnter}
          placeholder={placeholder}
          autoSize={{ minRows: 2, maxRows: 4 }}
          className="flex-1"
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
          添加
        </Button>
      </Space.Compact>

      {/* 提示 */}
      <div className="text-gray-400 text-sm mt-1">
        已选择 {value.length} 个单词
      </div>
    </div>
  );
};
