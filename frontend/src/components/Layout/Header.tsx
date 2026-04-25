/**
 * 页面头部组件
 */

import React from 'react';
import { BookOutlined } from '@ant-design/icons';

export const Header: React.FC = () => {
  return (
    <header className="h-14 border-b border-[#E5E5E5] flex items-center px-6 bg-[#FFFFFF]">
      <div className="flex items-center gap-2">
        <BookOutlined className="text-xl text-[#10A37F]" />
        <span className="text-lg font-semibold text-[#1A1A1A]">VocabWeaver</span>
        <span className="text-sm text-[#9B9B9B] ml-1">阅词</span>
      </div>
    </header>
  );
};
