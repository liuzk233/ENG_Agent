# VocabWeaver (词语编织者) - AI Agent 项目设计文档

## 1. 核心需求模块
* **数据萃取 (Data Extraction)**: 解析历年真题与官方大纲 -> 分词/词形还原 -> 提取高频词库与语法。
* **用户交互 (User Interaction)**: 用户输入目标记忆单词集合 + 指定文章风格（科幻/议论等）。
* **Agent 生成循环 (The Agent Loop)**: 根据输入生成短文 -> 严格执行超纲词汇自检 -> 自动迭代重写 / 支持用户手动刷新。

## 2. 架构设计：多智能体协作 (Multi-Agent Pattern)
采用 **“作者 (Writer) - 质检员 (Reviewer)”** 循环机制解决大语言模型难以执行“绝对负面约束（不能出现超纲词）”的痛点：
* **Writer Agent**: 负责根据单词和风格生成初稿。
* **Reviewer Agent**: 
    * *代码硬校验*: 对初稿进行分词，与大纲词库做差集比对，精准抓取超纲词。
    * *反馈机制*: 组装“超纲词及所在句子”的报错 Prompt，强制 Writer 替换简单词汇并重写。
* **循环限制**: 自动迭代 2-3 次，直至校验通过。

## 3. 技术栈选型 (MVP 导向)
* **核心语言**: Python 3.10+
* **大模型接口**: DeepSeek / Kimi / OpenAI (如 gpt-4o-mini)
* **NLP 处理**: `spaCy` (执行精确的 Tokenization 与 Lemmatization)
* **Agent 框架**: 纯原生 Python (`while` + `if/else`)，后期可平滑迁移至 `LangGraph`。
* **前端 UI**: `Streamlit` (快速构建带交互的 Web 页面)

## 4. 开发路线图 (Roadmap)
* **Phase 1 - 数据基建**: 处理真题与大纲，跑通文本清洗、停用词过滤逻辑，输出“必背词汇 Top 100”。
* **Phase 2 - 核心引擎**: 实现 `Drafting (初稿)` -> `Validating (校验)` -> `Refining (打磨)` 的 Agent 循环，确保终端能稳定输出无超纲词的达标文章。
* **Phase 3 - 界面包装**: 接入 Streamlit，实现侧边栏参数配置（选词、选风格）与主页面结果展示及重试交互。

## 5. 工程目录结构 (Project Structure)
遵循“高内聚、低耦合”原则，模块化管理业务逻辑与底层支撑：

```text
VocabWeaver/
│
├── data/                    # 本地数据存放区 (建议在 .gitignore 中忽略 raw 数据)
│   ├── raw/                 # 原始数据：历年真题PDF/TXT，官方词汇大纲原文件
│   └── processed/           # 处理后的数据：提取出的高频词库(JSON/CSV)，语法结构库
│
├── src/                     # 核心业务逻辑代码
│   ├── __init__.py
│   │
│   ├── data_pipeline/       # 模块一：数据萃取 (Phase 1)
│   │   ├── __init__.py
│   │   ├── extractor.py     # 负责读取 PDF/TXT 文本
│   │   └── nlp_processor.py # 负责调用 spaCy 进行分词、词形还原和词频统计
│   │
│   ├── agents/              # 模块二：Agent 核心生成模块 (Phase 2)
│   │   ├── __init__.py
│   │   ├── writer.py        # Writer Agent 逻辑：负责调用 LLM 生成初稿
│   │   ├── reviewer.py      # Reviewer Agent 逻辑：负责词汇校验、组装报错信息
│   │   └── orchestrator.py  # 调度器：控制 Writer 和 Reviewer 的 "生成-检查-修改" 循环
│   │
│   ├── prompts/             # 提示词管理 (单独抽离，方便后续调优)
│   │   ├── __init__.py
│   │   └── templates.py     # 存放 Writer 和 Reviewer 的系统提示词模板
│   │
│   └── utils/               # 通用工具类
│       ├── __init__.py
│       ├── llm_client.py    # 封装大模型 API 的调用代码 (如重试机制、错误处理)
│       └── config.py        # 加载环境变量和基础配置
│
├── tests/                   # 单元测试 (强烈建议写！尤其是词汇比对逻辑)
│   ├── test_nlp.py          # 测试分词逻辑是否准确
│   └── test_reviewer.py     # 测试 Reviewer 能否准确抓出超纲词
│
├── app.py                   # 模块三：UI 界面入口 (Phase 3，Streamlit 启动文件)
├── requirements.txt         # 项目依赖清单 (spaCy, openai, streamlit 等)
├── .env.example             # 环境变量配置模板 (说明需要哪些 API Key)
└── README.md                # 项目说明文档