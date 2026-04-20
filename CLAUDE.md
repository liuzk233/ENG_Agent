# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

VocabWeaver (词语编织者) 是一个 AI Agent 系统，用于生成包含用户指定词汇的英语文章，同时确保不出现超纲词汇（考研英语大纲）。系统采用 **Writer-Reviewer 多智能体架构**来解决大语言模型难以执行"负面约束"（不能出现超纲词）的痛点。

## 常用命令

```bash
# 启动 Streamlit Web 界面
streamlit run app.py

# 运行 CLI 测试（需配置大纲 XLS 文件路径）
python src/main.py

# 从 Markdown 文件构建 RAG 知识库
python src/data_pipeline/build_knowledge_base.py

# 运行测试
python -m pytest tests/
```

## 环境配置

1. 在项目根目录创建 `.env` 文件：
   ```
   DASHSCOPE_API_KEY="your-api-key"
   ```
2. 下载 spaCy 模型：`python -m spacy download en_core_web_sm`
3. 安装依赖：`pip install -r src/requirements.txt`

## 架构设计

### 多智能体模式（Writer → Reviewer 循环）

```
用户输入 → Orchestrator → [Writer 生成初稿] → [Reviewer 校验]
                    ↑                                ↓
                    └──────── [未通过则反馈重写] ─────┘
```

- **Orchestrator** (`src/agents/orchestrator.py`)：控制生成-校验循环，设置最大重试次数（默认 3 次）防止死循环
- **Writer** (`src/agents/writer.py`)：根据风格和目标词汇生成文章，支持 RAG 参考语料注入
- **Reviewer** (`src/agents/reviewer.py`)：使用 spaCy + lemminflect + LLM 智能过滤进行词汇校验

### RAG 系统

- **RAGRetriever** (`src/utils/rag_retriever.py`)：从 ChromaDB 检索参考语料用于风格 grounding
- **build_knowledge_base.py**：Markdown → 语义切片 → DashScope 向量化 → ChromaDB 存储
- 语义门控：目标词汇少于 2 个时跳过检索

### 数据流

```
data/raw/corpus/           # 原始 PDF/EPUB 文件（只读）
data/processed/markdown/   # 转换后的 Markdown 文件
data/vector_store/chromadb/# 向量数据库
```

## LLM 配置

使用阿里云 DashScope API（OpenAI 兼容格式）：
- Base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1`
- 模型：`qwen3.6-plus-2026-04-02`（可通过 `MODEL_NAME` 环境变量配置）
- Embedding：`text-embedding-v3`（1024 维）

## 词汇校验流水线

Reviewer 使用**级联架构**最小化误报：

1. **spaCy 分词** → 过滤非字母、专有名词、停用词
2. **英美拼写归一化**（colour→color, organise→organize 等）
3. **多策略词形还原**：spaCy lemma → lemminflect（遍历所有词性）→ snowball stemmer
4. **LLM 智能过滤**（最终兜底）：判断嫌疑词是否为"高中水平简单词"

## Prompt 模板

所有提示词集中管理于 `src/prompts/templates.py`：
- `WRITER_SYSTEM_PROMPT`：定义 Writer 角色和约束
- `FEW_SHOT_EXAMPLES`：高分范文示例（含倒装句、强调句等考点句式）
- `get_drafting_prompt()`：生成初稿提示词，支持注入 RAG 参考语料
- `get_refining_prompt()`：生成重写提示词，包含 Reviewer 反馈

## 关键文件

| 文件 | 用途 |
|------|------|
| `app.py` | Streamlit Web UI 入口 |
| `src/main.py` | CLI 测试入口 |
| `src/utils/config.py` | 环境变量和 API 配置 |
| `src/utils/llm_client.py` | OpenAI 兼容 LLM 客户端封装 |
| `src/data_pipeline/parsers/extractor.py` | 大纲 XLS 解析 |

## 大纲文件

大纲 XLS 文件路径在 `app.py` 和 `src/main.py` 中硬编码。文件格式要求：单词在第一列，含 `/` 的单词会被拆分（如 "a/an" → ["a", "an"]）。
