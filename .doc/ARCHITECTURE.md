# VocabWeaver 项目架构与实现指南

> **文档结构说明**：本文档采用渐进式披露原则，Phase 级别的技术细节存放于 `phases/` 子目录，按需查阅。

---

## 1. 项目目标 (Project Goals)

* 基于 Writer-Reviewer 架构，解决 LLM 生成过程中的"考研词汇负面约束"问题。
* 实现风格化多集连续故事生成，确保世界观、人物设定与词汇覆盖率的高度一致性。

---

## 2. 核心架构设计 (Architecture Design)

### 2.1 Agent 角色

| Agent | 职责 |
|-------|------|
| **Planner** | 生成多集大纲，分配目标词汇 |
| **Writer** | 挂载 Style-RAG，生成正文 |
| **Reviewer** | 词汇校验 + 兜底机制 |
| **Memory** | 状态持久化 + 断点续写 |

### 2.2 用户输入设计

| 模式 | 输入字段 | 触发场景 |
|------|----------|----------|
| **Initialize** | `total_episodes`, `target_words[]`, `user_id`, `style` | 首次创建故事 |
| **Continue** | `target_words[]`, `user_id`, `session_id` | 续写下一集 |

### 2.3 Graph 流程图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          VocabWeaver LangGraph 流程 v2.1                         │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   START     │
                              └──────┬──────┘
                                     │
                     ┌───────────────┴───────────────┐
                     │                               │
              Initialize Mode                 Continue Mode
                     │                               │
                     ▼                               ▼
          ┌──────────────────┐          ┌──────────────────┐
          │ Initialize Node  │          │ Load Memory Node │
          └────────┬─────────┘          └────────┬─────────┘
                   │                             │
                   └──────────┬──────────────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │   Planner Node     │
                   └──────────┬─────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │   Writer Node      │◄─────────────────┐
                   └──────────┬─────────┘                  │
                              │                            │
                              ▼                            │
                   ┌────────────────────┐                  │
                   │  Reviewer Node     │                  │
                   └──────────┬─────────┘                  │
                              │                            │
                    ┌─────────┴─────────┐                  │
                    │                   │                  │
               is_valid=True      is_valid=False           │
                    │                   │                  │
                    │                   ├──── retry < 5 ───┘
                    │                   │
                    │                   └─ retry ≥ 5 → Fallback
                    │                              │
                    │                              ├─ ratio ≤ 5% → Annotate & Pass
                    │                              ├─ adjust < 2 → Planner Adjust
                    │                              └─ adjust ≥ 2 → Force Annotate
                    │
                    ▼
          ┌──────────────────────┐
          │    Memory Node       │
          │ (PostgreSQL 持久化)  │
          └──────────┬───────────┘
                     │
            ┌────────┴────────┐
            │                 │
     episode < total     episode ≥ total
            │                 │
            ▼                 ▼
     ┌────────────┐     ┌──────────┐
     │  WAITING   │     │   END    │
     │ (断点续写) │     └──────────┘
     └────────────┘
            │
            │ 用户再次输入
            │
            └──────────► [Load Memory Node]
```

### 2.4 条件边路由逻辑

```python
def route_after_reviewer(state: GraphState) -> str:
    if state["is_valid"]:
        return "memory"
    
    if state["retry_count"] >= MAX_RETRIES:
        if state["out_of_scope_ratio"] <= 0.05:
            return "annotate_and_pass"
        if state["adjust_count"] >= MAX_ADJUSTS:
            return "force_annotate"
        return "planner_adjust"
    
    return "writer"
```

### 2.5 兜底机制

| 触发条件 | 分支 | 处理方式 |
|----------|------|----------|
| `retry >= 5` 且 `ratio <= 5%` | Annotate & Pass | 标注中文释义后通过 |
| `retry >= 5` 且 `ratio > 5%` 且 `adjust < 2` | Planner Adjust | 降密度重试 |
| `retry >= 5` 且 `adjust >= 2` | Force Annotate | 强制标注通过 |

---

## 3. GraphState 定义

```python
class GraphState(TypedDict):
    # 用户标识
    user_id: str
    session_id: str
    
    # 剧情控制
    total_episodes: int
    current_episode: int
    style: str
    
    # 大纲与词汇
    outline: List[str]
    target_words: List[str]
    used_words: List[str]
    
    # 生成内容
    draft_text: str
    final_text: str
    
    # 审查结果
    is_valid: bool
    feedback_list: List[str]
    out_of_scope_words: List[str]
    out_of_scope_ratio: float
    
    # 流程控制
    retry_count: int
    adjust_count: int
    fallback_mode: bool
    
    # 记忆管理
    story_bible: dict
    previous_summary: str
```

---

## 4. 技术栈选型

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 框架 | LangGraph | State 机制 + Conditional Edges |
| 向量数据库 | Milvus | HNSW + Trie 混合索引 |
| 关系数据库 | PostgreSQL | 记忆持久化，支持高并发 |
| LLM | DashScope (Qwen) | OpenAI 兼容接口 |
| Embedding | BGE-M3 / DashScope | 1024 维向量 |

---

## 5. 基础设施

### 5.1 服务架构

```
┌─────────────────────────────────────────────────────┐
│                   Docker Compose                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Milvus    │  │  PostgreSQL │  │  (Optional) │ │
│  │  :19530     │  │   :5432     │  │  Redis      │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 5.2 数据库 Schema 概览

| 表名 | 用途 | 主键 |
|------|------|------|
| `sessions` | 会话元信息 | `user_id + session_id` |
| `story_bibles` | 故事圣经 | `session_id` |
| `episode_states` | 集数状态快照 | `session_id + episode_num` |
| `vocabulary_progress` | 词汇使用记录 | `session_id + word` |

> 详细 Schema 定义见 [phases/phase-0-infrastructure.md](phases/phase-0-infrastructure.md)

---

## 6. 实施路径

### 进度概览

| Phase | 状态 | 文档 |
|-------|------|------|
| Phase 0: 基础设施部署 | ✅ 已完成 | [phase-0-infrastructure.md](phases/phase-0-infrastructure.md) |
| Phase 1: LangGraph 骨架 | ✅ 已完成 | [phase-1-langgraph-skeleton.md](phases/phase-1-langgraph-skeleton.md) |
| Phase 2: 数据灌库 | ✅ 已完成 | [phase-2-data-ingestion.md](phases/phase-2-data-ingestion.md) |
| Phase 3: Agent 实现 | ✅ 已完成 | [phase-3-agents.md](phases/phase-3-agents.md) |
| Phase 4: 全链路测试 | ✅ 已完成 | [phase-4-integration.md](phases/phase-4-integration.md) |

### Phase 清单

- [x] **Phase 0**: 基础设施部署
  - Docker Compose 配置（Milvus + PostgreSQL）
  - 数据库 Schema 初始化
  - 环境变量配置

- [x] **Phase 1**: LangGraph 状态定义与 Graph 骨架
  - 定义 GraphState (TypedDict)
  - 定义 Node 函数签名
  - 定义条件边路由逻辑
  - 编译空 Graph 验证流转

- [x] **Phase 2**: 数据源头清洗与灌库
  - Markdown 切片 + 词汇软过滤
  - Milvus 混合索引构建
  - Embedder 工厂模式

- [x] **Phase 3**: 实现 Agent 逻辑
  - Reviewer Agent（词汇校验 + 兜底机制）
  - Writer Agent（Style-RAG）
  - Planner Agent（词汇分配）
  - Memory Agent（PostgreSQL 持久化）

- [x] **Phase 4**: 全链路串联与测试
  - Graph 组装与编译
  - 多集连载测试
  - 断点续写测试
  - 兜底机制测试

---

## 7. 避坑与约束

| 约束 | 说明 |
|------|------|
| **词汇污染** | RAG 检索片段必须经过词汇过滤，避免 Few-shot 污染 |
| **状态管理** | 禁止依赖 LLM 维护状态，必须显式读写数据库 |
| **重试保护** | `retry_count >= 5` + `adjust_count >= 2` 双重保护 |
| **记忆隔离** | 数据库查询必须带 `user_id` + `session_id` 条件 |

---

## 8. 文档索引

```
.doc/
├── ARCHITECTURE.md              # 本文档（架构概览）
├── phases/
│   ├── phase-0-infrastructure.md    # Phase 0 技术细节
│   ├── phase-1-langgraph-skeleton.md # Phase 1 技术细节
│   ├── phase-2-data-ingestion.md    # Phase 2 技术细节
│   ├── phase-3-agents.md            # Phase 3 技术细节
│   └── phase-4-integration.md       # Phase 4 技术细节
└── daily-log/                   # 开发日志
```
