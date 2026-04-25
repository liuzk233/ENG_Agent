/**
 * 风格选择组件
 */

import React from 'react';
import { Select } from 'antd';
import { STYLE_OPTIONS } from '@/types';

interface StyleSelectProps {
  value: string;
  onChange: (value: string) => void;
}

export const StyleSelect: React.FC<StyleSelectProps> = ({ value, onChange }) => {
  return (
    <Select
      value={value}
      onChange={onChange}
      options={STYLE_OPTIONS.map((opt) => ({
        value: opt.value,
        label: opt.label,
      }))}
      className="w-full"
    />
  );
};
