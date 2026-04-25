/**
 * 进度面板组件
 *
 * 显示生成流程的节点状态和进度
 */

import React from 'react';
import { Card, Steps, Tag, Alert, Progress } from 'antd';
import {
  LoadingOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import type { NodeState, NodeStatus } from '@/types';

interface ProgressPanelProps {
  nodes: Record<string, NodeState>;
  currentEpisode: number;
  totalEpisodes: number;
}

const NODE_LABELS: Record<string, string> = {
  initialize: '初始化',
  load_memory: '加载记忆',
  planner: '大纲规划',
  writer: '内容生成',
  reviewer: '词汇审查',
  annotate_and_pass: '标注通过',
  planner_adjust: '词汇调整',
  force_annotate: '强制通过',
  memory: '状态保存',
};

const NODE_ORDER = ['initialize', 'planner', 'writer', 'reviewer', 'memory'];

const getStatusIcon = (status: NodeStatus) => {
  switch (status) {
    case 'running':
      return <LoadingOutlined style={{ color: '#1890ff' }} />;
    case 'success':
      return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
    case 'failed':
      return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
    default:
      return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
  }
};

const getStepStatus = (status: NodeStatus): 'wait' | 'process' | 'finish' | 'error' => {
  switch (status) {
    case 'running':
      return 'process';
    case 'success':
      return 'finish';
    case 'failed':
      return 'error';
    default:
      return 'wait';
  }
};

export const ProgressPanel: React.FC<ProgressPanelProps> = ({
  nodes,
  currentEpisode,
  totalEpisodes,
}) => {
  // 过滤并排序显示的节点
  const displayNodes = NODE_ORDER.filter((node) => nodes[node]);

  // 获取超纲词
  const reviewerNode = nodes.reviewer;
  const outOfScopeWords = reviewerNode?.outOfScopeWords || [];

  return (
    <Card title="生成进度" className="w-full">
      {/* 集数进度 */}
      <div className="mb-6">
        <div className="flex justify-between mb-2">
          <span className="text-gray-600">当前进度</span>
          <span className="text-gray-800 font-medium">
            第 {currentEpisode} / {totalEpisodes} 集
          </span>
        </div>
        <Progress
          percent={Math.round((currentEpisode / totalEpisodes) * 100)}
          status="active"
        />
      </div>

      {/* 节点状态 */}
      <Steps direction="vertical" current={-1} size="small">
        {displayNodes.map((node) => {
          const nodeState = nodes[node];
          return (
            <Steps.Step
              key={node}
              title={NODE_LABELS[node] || node}
              icon={getStatusIcon(nodeState.status)}
              status={getStepStatus(nodeState.status)}
              description={
                nodeState.retryCount !== undefined &&
                nodeState.retryCount > 0 && (
                  <Tag color="orange">重试 {nodeState.retryCount} 次</Tag>
                )
              }
            />
          );
        })}
      </Steps>

      {/* 超纲词警告 */}
      {outOfScopeWords.length > 0 && (
        <Alert
          type="warning"
          message="检测到超纲词汇"
          description={
            <div className="mt-2">
              {outOfScopeWords.map((word, index) => (
                <Tag key={index} color="warning" className="mb-1">
                  {word}
                </Tag>
              ))}
            </div>
          }
          showIcon
          className="mt-4"
        />
      )}
    </Card>
  );
};
