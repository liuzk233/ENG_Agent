# Phase 3: Agent 实现

> 状态：✅ 已完成 (2026-04-20)

---

## 1. 目标

实现四个核心 Agent 的业务逻辑，填充 Phase 1 定义的 Node 骨架。

---

## 2. Agent 清单

| Agent | 对应 Node | 核心职责 |
|--------|-----------|----------|
| Reviewer | `reviewer_node` | 词汇校验 + 兜底机制 |
| Writer | `writer_node` | Style-RAG + 正文生成 |
| Planner | `planner_node` | 大纲生成 + 词汇分配 |
| Memory | `load_memory_node`, `memory_node` | PostgreSQL 持久化 |

---

## 3. Reviewer Agent

### 3.1 文件位置

`src/agents/reviewer.py`（已有部分实现）

### 3.2 词汇校验流水线

```
输入文本
    ↓
[spaCy 分词] → 过滤非字母、专有名词、停用词
    ↓
[英美拼写归一化] → colour→color, organise→organize
    ↓
[词形还原] → spaCy lemma → lemminflect → snowball stemmer
    ↓
[大纲词表匹配] → 检测超纲词
    ↓
[LLM 智能过滤] → 判断嫌疑词是否"高中水平简单词"
    ↓
输出: is_valid, feedback_list, out_of_scope_words
```

### 3.3 兜底机制实现

**触发条件**：`retry_count >= MAX_RETRIES`

**处理逻辑**：
1. 计算超纲词占比：`out_of_scope_ratio = len(out_of_scope_words) / total_words`
2. 判断分支：
   - `ratio <= 5%`：标注中文释义后通过
   - `ratio > 5%` 且 `adjust_count < 2`：返回 `planner_adjust`
   - `ratio > 5%` 且 `adjust_count >= 2`：强制标注通过

### 3.4 中文释义标注

- 调用翻译 API 或词典获取中文释义
- 格式：`word (中文释义)`
- 示例：`The ephemeral (短暂的) nature of life...`

### 3.5 Node 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_valid` | bool | 是否通过 |
| `feedback_list` | List[str] | 反馈信息 |
| `out_of_scope_words` | List[str] | 超纲词列表 |
| `out_of_scope_ratio` | float | 超纲词占比 |
| `fallback_text` | str | 兜底标注文本（可选） |

---

## 4. Writer Agent

### 4.1 文件位置

`src/agents/writer.py`

### 4.2 Style-RAG 集成

```
target_words + style
        ↓
[MilvusRAGRetriever.retrieve()]
        ↓
相关语料片段 (top_k=5)
        ↓
[注入 Prompt]
        ↓
[LLM 生成]
        ↓
draft_text
```

### 4.3 Prompt 组装

**输入来源**：
- `outline[current_episode]`：当前集大纲
- `target_words`：目标词汇
- `feedback_list`：审查反馈（重写时）
- `previous_summary`：前情提要（续写时）
- RAG 检索结果：风格参考片段

**Prompt 模板位置**：`src/prompts/templates.py`

### 4.4 Node 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `draft_text` | str | 生成的草稿 |

---

## 5. Planner Agent

### 5.1 文件位置

`src/agents/planner.py`

### 5.2 大纲生成策略

**Initialize 模式**：
1. 根据 `total_episodes` 生成 N 集大纲
2. 将 `target_words` 分配到各集
3. 确保每集词汇分布均匀

**Planner Adjust 模式**：
1. 降低当前集词汇密度
2. 将部分词汇转移至后续集数
3. 更新 `outline` 和 `target_words`

### 5.3 词汇分配算法

考虑因素：
- 词汇难度均衡
- 剧情连贯性
- 每集词汇数量上限

### 5.4 Node 输出

| 字段 | 类型 | 说明 |
|------|------|------|
| `outline` | List[str] | 更新后的大纲 |
| `target_words` | List[str] | 更新后的目标词汇 |
| `retry_count` | int | 重置为 0（Adjust 模式） |
| `adjust_count` | int | 递增（Adjust 模式） |

---

## 6. Memory Agent

### 6.1 文件位置

`src/memory/manager.py`

### 6.2 数据库操作

**Load Memory Node**：
- 查询 `sessions` 表恢复会话状态
- 查询 `story_bibles` 表获取故事设定
- 查询 `episode_states` 表获取最新集数状态
- 查询 `vocabulary_progress` 表获取词汇使用记录

**Memory Node**：
- 更新 `sessions.current_episode`
- 插入 `episode_states` 记录
- 更新 `vocabulary_progress` 记录
- 更新 `story_bibles`（如有变更）

### 6.3 上下文压缩

**微压缩**：
- 保留最近 3 轮纠错记录
- 旧文本替换为占位符

**自动折叠**：
- Token 超阈值时触发
- LLM 生成前情提要
- 完整文本存入 `transcript` 字段

### 6.4 记忆隔离

所有查询必须带条件：
```sql
WHERE user_id = :user_id AND session_id = :session_id
```

### 6.5 Node 输出

**Load Memory Node**：
| 字段 | 类型 | 说明 |
|------|------|------|
| 恢复的 GraphState 字段 | - | 从数据库恢复 |

**Memory Node**：
| 字段 | 类型 | 说明 |
|------|------|------|
| `current_episode` | int | 递增 |
| `previous_summary` | str | 更新的前情提要 |

---

## 7. 依赖关系

```
Phase 1 (GraphState 骨架)
        ↓
Phase 2 (MilvusRAGRetriever 可用)
        ↓
Phase 3 (Agent 实现)
    ├── Reviewer 依赖: 大纲词表
    ├── Writer 依赖: MilvusRAGRetriever, Prompt 模板
    ├── Planner 依赖: LLM
    └── Memory 依赖: PostgreSQL 连接
```

---

## 8. 测试策略

### 8.1 单元测试

- Reviewer：词汇校验逻辑、兜底机制分支
- Writer：RAG 检索调用、Prompt 组装
- Planner：词汇分配算法
- Memory：数据库 CRUD

### 8.2 集成测试

- Writer → Reviewer 循环
- 兜底机制完整路径
- PostgreSQL 持久化与恢复

---

## 9. 文件清单

| 文件 | 用途 |
|------|------|
| `src/agents/reviewer.py` | Reviewer Agent（已有） |
| `src/agents/writer.py` | Writer Agent |
| `src/agents/planner.py` | Planner Agent |
| `src/memory/manager.py` | Memory Agent |
| `src/prompts/templates.py` | Prompt 模板 |
| `tests/test_agents.py` | Agent 单元测试 |
