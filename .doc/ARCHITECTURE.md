# VocabWeaver 项目架构与实现指南 (扩展版)

## 1. 项目目标 (Project Goals)
* 基于 Writer-Reviewer 架构，解决 LLM 生成过程中的“考研词汇负面约束”问题。
* 实现风格化多集连续故事生成，确保世界观、人物设定与词汇覆盖率的高度一致性。

## 2. 核心架构设计 (Architecture Design)
升级为“四核驱动” Agent 框架。为了最大化控制力和可追溯性，**全系统由 LangGraph 作为中枢神经进行编排**：
* **Planner Agent (统筹编剧)**：生成 10 集大纲，将目标词汇科学分配至各章节。
* **Writer Agent (主笔)**：挂载 Style-RAG，吸收特定风格片段，负责正文生成。
* **Reviewer Agent (合规审查)**：执行“负面约束”校验，识别超纲词并标注。
* **Memory Agent (记忆管家)**：维护显式状态机，执行上下文动态压缩，管理“故事圣经”。

### 2.1 LangGraph 核心工作流 (Workflow Orchestration)
本项目的核心难点在于“审查与重写”以及“长线上下文传递”，这些将完全映射到 LangGraph 的流转机制中：
* **全局状态 (Global State)**：定义一个极其严格的 `TypedDict` 或 `Pydantic` Schema，包含 `current_episode` (当前集数), `draft_text` (草稿正文), `review_feedback` (审查意见), `retry_count` (重试次数) 等变量。这构成了 Agent 之间共享的“短期工作记忆”。
* **节点 (Nodes)**：四大 Agent 分别映射为 LangGraph 中的四个核心 Node。
* **条件边 (Conditional Edges)**：
  * **对抗生成循环**：`Writer Node` -> `Reviewer Node`。如果在 Reviewer 节点发现超纲词，触发条件边**打回 (Route Back)** 给 `Writer Node`；如果合规，则流转至 `Memory Node`。
  * **长线连载循环**：`Memory Node` -> 更新本地 JSON -> 触发条件边进入下一集 (回到 `Planner Node` 或 `Writer Node`)。

## 3. 技术栈选型 (Tech Stack)
* **框架**：LangGraph (利用其 State 机制实现 Agent 间的强一致性流转，利用 Conditional Edges 处理对抗生成循环)。
* **记忆层**：放弃 Mem0/Zep 等黑盒向量记忆，采用“显式状态 JSON + 动态滑动摘要”架构。
* **风格化 RAG**：DSPy (优化 Few-shot) + Milvus (存储经过词汇过滤的大师文风片段)。

## 4. 深度记忆管理策略 (Memory Management Strategy)
为了保证长线叙事不“穿帮”且不违反词汇约束，系统采用三层记忆过滤机制：

### A. 静态层：故事圣经 (Story Bible - The "CLAUDE.md" Pattern)
* **内容**：存储核心设定、人物关系表、已使用的目标词汇、考研词汇白名单。
* **机制**：作为 invariant（不可变量）永远挂载在所有 Agent 提示词的最顶部。
* **作用**：确保第 10 集的主角性格与第 1 集完全一致，且 Agent 永远知道哪些词是“禁区”。

### B. 事实层：显式状态机 (Explicit State Machine)
* **实现**：设计独立的状态管理组件，将剧情关键节点抽象并存储为本地 JSON 文件，确保状态流转清晰可查。
* **管理内容**：
  * `Character_States.json`：记录人物位置、持有道具、好感度。
  * `Vocabulary_Progress.json`：记录每个目标词汇的出现次数及上下文。
* **同步机制**：当 LangGraph 流转至 Memory Node 时，必须调用 `update_state` 工具，强制更新 JSON 文件。下一章生成时，Planner Node 会先读取该文件以确定起始条件。

### C. 动态层：三级上下文压缩 (Context Compaction Pipeline)
为了防止长线对话导致模型注意力涣散（Lost in the middle），引入以下压缩策略：
1. **微压缩 (Micro-compact)**：在 LangGraph 的 `Writer <-> Reviewer` 循环中，仅在 State 中保留最近 3 轮的纠错记录。对于被驳回的包含“超纲词”的旧文本，自动替换为占位符 `[Error: Content rejected due to out-of-syllabus words]`。
2. **自动折叠 (Auto-compact)**：当单集生成的 Token 超过阈值时，在 LangGraph 中触发 `Compact Node`。
   * **摘要生成**：LLM 将前序剧情压缩为“前情提要”，包含：1) 已发生的关键事件，2) 待解决的伏笔，3) 必须继承的语气特征。
   * **冷备份**：将完整的逐字稿保存至 `.transcripts/` 目录供人工追溯。
3. **身份重注 (Identity Re-injection)**：在上下文被剧烈压缩后，系统会在下一轮 Prompt 中强行注入身份确认信息，防止模型因记忆断层而改变叙事口吻。

## 5. 实施路径 (Implementation Phases)
* [x] **Phase 1**: 搭建基础项目骨架与 LangGraph 状态定义。
  * 确立项目目录结构。
  * **[核心]** 在 `state.py` 中定义 LangGraph 的全局 `GraphState` (TypedDict)，明确流转所需的所有变量及其 Reducer 逻辑。
* [ ] **Phase 2**: 数据源头清洗与重新灌库 (Data Cleansing & Re-ingestion)。
  * 建立 `scripts/data_ingestion/` 独立基础流水线。
  * **强制词汇审查 (Pre-filtering)**：实现校验脚本，替换包含超纲词的风格片段，确保语料池绝对纯净。
  * **元数据打标**：为切块数据打上强类型的标量标签（如 `genre: suspense`）。
  * **向量建库**：将处理好的数据灌入 Milvus，并建立混合索引。
* [ ] **Phase 3**: 实现 Reviewer Agent 逻辑。
  * 集成考研词汇词典，实现正则/语义双重过滤。
  * 定义其在 LangGraph 中的输出格式：返回布尔值 `is_valid` 及 `feedback_list`，直接写入 GraphState。
* [ ] **Phase 4**: 搭建 Style-RAG 与 Writer Agent。
  * 使用 DSPy 优化文风，确保检索出的示例不含超纲词。
  * 组装 Writer Node：读取 GraphState 中的大纲与反馈，调用大模型生成正文，并更新 GraphState。
* [ ] **Phase 5**: 构建 Memory Agent 与持久化状态机。
  * 实现 Memory Node：负责从 GraphState 提取剧情增量，更新 `characters.json` 等静态文件。
  * 实现 `ContextCompactor` 逻辑，处理 Token 水位。
* [ ] **Phase 6**: LangGraph 全链路串联与长线叙事压力测试。
  * 组装 Graph：将前几阶段编写的独立函数封装为 LangGraph 的 Nodes。
  * 定义 Edges：编写核心路由逻辑 `route_after_review`，依据 `GraphState["is_valid"]` 决定是回到 Writer Node 还是进入 Memory Node。
  * 编译并运行图，进行多集连载测试。

## 6. 避坑与约束 (Constraints & Anti-patterns)
* **严禁词汇污染**：RAG 检索回来的文风片段（Few-shot）必须经过 Reviewer 同款词典过滤。如果 Few-shot 里含有高级词汇，Writer 会产生“模仿幻觉”，从而不断产生超纲词。
* **禁止依赖 LLM 维护状态**：绝不要问 LLM “主角现在手里有什么”，必须让 Memory Node 显式读取 `read_state_json` 并注入到 GraphState 中。
* **限制重试死循环**：在 LangGraph 的 `GraphState` 中必须设置 `retry_count` 字段。如果 Writer 和 Reviewer 的循环超过 5 次，必须强制跳出循环，由 Planner 降低词汇密度要求或抛出异常，防止 Token 消耗失控。