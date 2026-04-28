# CLAUDE.md

This file provides guidance for Claude Code when working with code in this repository.

## 项目概述

**VocabWeaver (词语编织者)** 是一个基于 LangGraph 的多智能体英语文章生成系统。核心目标是生成包含用户指定词汇的英语文章，同时确保不出现超纲词汇（考研英语大纲）。

系统采用 **Writer-Reviewer 多智能体架构** 解决大语言模型难以执行"负面约束"（不能出现超纲词）的痛点。

## 项目状态

| Phase | 状态 | 说明 |
|-------|------|------|
| Phase 0: 基础设施 | ✅ 已完成 | Docker Compose (Milvus + PostgreSQL) |
| Phase 1: LangGraph 骨架 | ✅ 已完成 | State, Nodes, Edges, Graph |
| Phase 2: 数据灌库 | ✅ 已完成 | Milvus 向量检索 + 词汇软过滤 |
| Phase 3: Agent 实现 | ✅ 已完成 | Writer, Reviewer, Planner, Memory |
| Phase 4: 全链路测试 | ✅ 已完成 | 集成测试 + 端到端测试 |
| Phase 5: 前端交互 | ✅ 已完成 | FastAPI + React + WebSocket |

## 常用命令

```bash
# 启动 Streamlit Web 界面
streamlit run app.py

# 运行 CLI 测试（需配置 .env 和大纲文件）
python src/main.py

# 运行测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_integration.py -v

# 构建 Milvus 知识库
python src/rag/builder.py --input data/processed/markdown
```

## 环境配置

1. 创建 `.env` 文件：
   ```
   DASHSCOPE_API_KEY="your-api-key"
   MILVUS_HOST=localhost
   MILVUS_PORT=19530
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   VECTOR_STORE_TYPE=milvus
   ```

2. 安装依赖：`pip install -r src/requirements.txt`

3. 下载 spaCy 模型：`python -m spacy download en_core_web_sm`

4. 启动 Docker 服务：`docker-compose -f Milvus/docker-compose.yml up -d`

## 核心架构

### LangGraph 流程图

```
START
  ↓
[条件边: route_entry_point]
  ├─→ initialize_node ─→ planner_node ─→ writer_node ─→ reviewer_node
  │                                                        ↓
  └─→ load_memory_node ─→ planner_node ─→ writer_node ─→ reviewer_node
                                                           ↓
                                              [条件边: route_after_reviewer]
                                                ├─→ memory_node (通过)
                                                ├─→ writer (重试)
                                                ├─→ annotate_and_pass (低比例兜底)
                                                ├─→ planner_adjust (高比例调整)
                                                └─→ force_annotate (强制通过)
                                                           ↓
                                              [条件边: route_after_memory]
                                                ├─→ END (完成)
                                                └─→ END/waiting (等待续写)
```

### GraphState 核心字段

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
    retry_count: int          # 最大 5 次
    adjust_count: int         # 最大 2 次
    fallback_mode: bool
```

### 兜底机制

| 条件 | 分支 | 处理方式 |
|------|------|----------|
| `retry >= 5` 且 `ratio <= 5%` | annotate_and_pass | 标注中文释义后通过 |
| `retry >= 5` 且 `ratio > 5%` 且 `adjust < 2` | planner_adjust | 降低词汇密度重试 |
| `retry >= 5` 且 `adjust >= 2` | force_annotate | 强制标注通过 |

### 多智能体职责

| Agent | 文件 | 职责 |
|-------|------|------|
| **Reviewer** | `src/agents/reviewer.py` | 词汇校验（spaCy + lemminflect + LLM 兜底） |
| **Writer** | `src/agents/writer.py` | 正文生成（支持 RAG 风格参考） |
| **Planner** | `src/agents/planner.py` | 大纲生成 + 词汇分配 |
| **Memory** | `src/memory/manager.py` | PostgreSQL 持久化 |

## 关键文件

| 文件 | 用途 |
|------|------|
| `app.py` | Streamlit Web UI 入口 |
| `src/main.py` | CLI 测试入口 |
| `src/graph/graph.py` | LangGraph 组装与编译 |
| `src/graph/state.py` | GraphState 定义 + 常量 |
| `src/graph/nodes.py` | Node 函数实现 |
| `src/graph/edges.py` | 条件边路由逻辑 |
| `src/agents/reviewer.py` | 词汇校验流水线 |
| `src/rag/retriever.py` | Milvus 向量检索器 |
| `src/memory/manager.py` | PostgreSQL CRUD |
| `src/utils/config.py` | 环境变量配置 |
| `src/prompts/templates.py` | Prompt 模板集中管理 |

## 数据流

```
data/raw/corpus/           # 原始 PDF/EPUB 文件
    ↓
data/processed/markdown/   # 转换后的 Markdown
    ↓
src/rag/builder.py         # 切片 + 向量化
    ↓
Milvus (向量存储)           # 混合索引 (HNSW + Trie)
    ↓
src/rag/retriever.py       # RAG 检索
```

## LLM 配置

- **Provider**: 阿里云 DashScope (OpenAI 兼容格式)
- **Base URL**: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- **Model**: `qwen3.6-plus-2026-04-02`
- **Embedding**: `text-embedding-v3` (1024 维)

## 词汇校验流水线

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
输出: is_valid, feedback, out_of_scope_words
```

## 数据库 Schema

| 表名 | 用途 | 主键 |
|------|------|------|
| `sessions` | 会话元信息 | `user_id + session_id` |
| `story_bibles` | 故事圣经 | `session_id` |
| `episode_states` | 集数状态快照 | `session_id + episode_num` |

## 测试文件

| 文件 | 用途 |
|------|------|
| `tests/test_agents.py` | Agent 单元测试 |
| `tests/test_graph_flow.py` | Graph 流转测试 |
| `tests/test_integration.py` | 集成测试 |
| `tests/test_e2e.py` | 端到端测试 |

## 避坑指南

| 约束 | 说明 |
|------|------|
| **词汇污染** | RAG 检索片段必须经过词汇软过滤 (`is_vocabulary_clean=true`) |
| **状态管理** | 禁止依赖 LLM 维护状态，必须显式读写 PostgreSQL |
| **重试保护** | `retry_count >= 5` + `adjust_count >= 2` 双重保护防止死循环 |
| **记忆隔离** | 数据库查询必须带 `user_id` + `session_id` 条件 |
| **大纲文件** | 需要配置正确的 `.xls` 大纲文件路径 |

## 架构文档

详细设计文档位于 `.doc/` 目录：

- `ARCHITECTURE.md` - 整体架构设计
- `phases/phase-0-infrastructure.md` - Docker 基础设施
- `phases/phase-1-langgraph-skeleton.md` - LangGraph 骨架
- `phases/phase-2-data-ingestion.md` - 数据灌库
- `phases/phase-3-agents.md` - Agent 实现
- `phases/phase-4-integration.md` - 全链路测试

---

## 行为准则

**权衡原则：** 这些准则倾向于谨慎而非速度。对于简单任务，请自行判断。

### 1. 编码前先思考

- 明确陈述假设。如果不确定，先问。
- 如果存在多种理解，请全部列出。
- 如果存在更简单的方案，请说明。
- 如果有不清楚的地方，停下来问。

### 2. 简单优先

- 不要实现未被要求的功能。
- 不要为单次使用的代码创建抽象。
- 不要为不可能发生的场景编写错误处理。

### 3. 精准修改

- 只修改必须修改的部分。
- 保持现有代码风格。
- 每一行修改都应该能追溯到用户的请求。

### 4. 目标驱动

将任务转化为可验证的目标：
- "添加验证" → "编写测试用例，然后让测试通过"
- "修复 Bug" → "编写一个能复现问题的测试"
