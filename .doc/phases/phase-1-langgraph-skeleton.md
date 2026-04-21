# Phase 1: LangGraph 状态定义与 Graph 骨架

> 状态：🚧 进行中

---

## 1. 目标

定义 LangGraph 的核心骨架，包括 State、Node 函数签名和条件边路由逻辑。

---

## 2. 构建原则

**先定义 State 合约，再填充 Agent 实现。**

顺序：
1. State 定义 → 所有 Agent 的"接口合约"
2. Node 函数签名 → 明确输入输出类型
3. Edges 路由逻辑 → 条件分支定义
4. 空骨架验证 → 确保流转正确
5. Agent 实现填充 → 后续 Phase

---

## 3. GraphState 定义

### 3.1 文件位置

`src/graph/state.py`

### 3.2 字段分组

| 分组 | 字段 | 类型 | 说明 |
|------|------|------|------|
| 用户标识 | `user_id` | str | 用户ID |
| 用户标识 | `session_id` | str | 会话ID |
| 剧情控制 | `total_episodes` | int | 预期总集数 |
| 剧情控制 | `current_episode` | int | 当前集数 |
| 剧情控制 | `style` | str | 风格设定 |
| 大纲与词汇 | `outline` | List[str] | 各集大纲 |
| 大纲与词汇 | `target_words` | List[str] | 当前集目标词汇 |
| 大纲与词汇 | `used_words` | List[str] | 已使用目标词汇 |
| 生成内容 | `draft_text` | str | 当前草稿 |
| 生成内容 | `final_text` | str | 最终文本 |
| 审查结果 | `is_valid` | bool | 是否通过审查 |
| 审查结果 | `feedback_list` | List[str] | 审查反馈 |
| 审查结果 | `out_of_scope_words` | List[str] | 超纲词列表 |
| 审查结果 | `out_of_scope_ratio` | float | 超纲词占比 |
| 流程控制 | `retry_count` | int | 当前重试次数 |
| 流程控制 | `adjust_count` | int | Planner 调整次数 |
| 流程控制 | `fallback_mode` | bool | 是否触发兜底 |
| 记忆管理 | `story_bible` | dict | 故事圣经 |
| 记忆管理 | `previous_summary` | str | 前情提要 |

---

## 4. Node 函数签名

### 4.1 文件位置

`src/graph/nodes.py`

### 4.2 Node 列表

| Node | 输入 | 输出 | 职责 |
|------|------|------|------|
| `initialize_node` | `user_id`, `total_episodes`, `style`, `target_words` | `session_id`, `story_bible` | 创建新会话 |
| `load_memory_node` | `user_id`, `session_id` | 恢复的 GraphState | 加载历史状态 |
| `planner_node` | `target_words`, `story_bible` | `outline`, `assigned_words` | 生成大纲 |
| `writer_node` | `outline`, `feedback_list`, `previous_summary` | `draft_text` | 生成正文 |
| `reviewer_node` | `draft_text`, `target_words` | `is_valid`, `feedback_list`, `out_of_scope_ratio` | 词汇校验 |
| `memory_node` | `final_text`, `story_bible` | 持久化状态 | 保存状态 |

### 4.3 函数签名模式

每个 Node 函数遵循 LangGraph 规范：
- 参数：`state: GraphState`
- 返回：`dict`（部分状态更新）

---

## 5. 条件边路由

### 5.1 文件位置

`src/graph/edges.py`

### 5.2 路由函数

| 函数 | 判断逻辑 | 返回值 |
|------|----------|--------|
| `route_after_reviewer` | `is_valid` → `retry_count` → `out_of_scope_ratio` → `adjust_count` | `memory` / `writer` / `annotate_and_pass` / `planner_adjust` / `force_annotate` |
| `route_after_memory` | `current_episode` vs `total_episodes` | `end` / `waiting` |

### 5.3 路由逻辑详解

**route_after_reviewer**:
```
is_valid=True → memory
is_valid=False:
  retry < 5 → writer (retry++)
  retry >= 5:
    ratio <= 5% → annotate_and_pass
    ratio > 5%:
      adjust < 2 → planner_adjust
      adjust >= 2 → force_annotate
```

**route_after_memory**:
```
episode < total → waiting (等待用户输入)
episode >= total → end
```

---

## 6. Graph 组装

### 6.1 文件位置

`src/graph/graph.py`

### 6.2 组装步骤

1. 创建 `StateGraph(GraphState)`
2. 添加所有 Node
3. 设置 Entry Point（根据输入模式）
4. 添加普通 Edge
5. 添加条件 Edge
6. 编译 Graph

### 6.3 Edge 连接关系

```
START → initialize_node (Initialize 模式)
START → load_memory_node (Continue 模式)

initialize_node → planner_node
load_memory_node → planner_node

planner_node → writer_node

writer_node → reviewer_node

reviewer_node → [条件边] → memory_node / writer / annotate_and_pass / planner_adjust / force_annotate

annotate_and_pass → memory_node
planner_adjust → planner_node
force_annotate → memory_node

memory_node → [条件边] → END / WAITING
```

---

## 7. 验证步骤

### 7.1 单元测试

- 测试每个 Node 返回正确的状态更新
- 测试条件边路由逻辑正确
- 测试死循环保护机制

### 7.2 流转验证

使用 Mock Agent 验证完整流转：
1. Initialize → Planner → Writer → Reviewer → Memory → End
2. Initialize → Planner → Writer → Reviewer → Writer (retry) → ...
3. 触发兜底机制路径

---

## 8. 文件清单

| 文件 | 用途 |
|------|------|
| `src/graph/__init__.py` | 模块导出 |
| `src/graph/state.py` | GraphState 定义 |
| `src/graph/nodes.py` | Node 函数骨架 |
| `src/graph/edges.py` | 条件边路由 |
| `src/graph/graph.py` | Graph 组装与编译 |
| `tests/test_graph_flow.py` | 流转测试 |
