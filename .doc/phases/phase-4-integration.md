# Phase 4: 全链路串联与测试

> 状态：✅ 已完成 (2026-04-20)

---

## 1. 目标

将 Phase 3 实现的 Agent 组装到 LangGraph 中，进行端到端测试。

---

## 2. Graph 组装

### 2.1 文件位置

`src/graph/graph.py`

### 2.2 组装流程

```
1. 导入所有 Agent 函数
2. 创建 StateGraph(GraphState)
3. 添加 Node：
   - initialize_node
   - load_memory_node
   - planner_node
   - writer_node
   - reviewer_node
   - annotate_and_pass (辅助节点)
   - planner_adjust (辅助节点)
   - force_annotate (辅助节点)
   - memory_node
4. 设置 Entry Point（根据输入模式动态选择）
5. 添加 Edge：
   - initialize_node → planner_node
   - load_memory_node → planner_node
   - planner_node → writer_node
   - writer_node → reviewer_node
6. 添加条件 Edge：
   - reviewer_node → route_after_reviewer
   - memory_node → route_after_memory
7. 编译 Graph
```

### 2.3 Entry Point 选择

```python
def determine_entry_point(input_data: dict) -> str:
    if "total_episodes" in input_data:
        return "initialize_node"
    else:
        return "load_memory_node"
```

---

## 3. 测试场景

### 3.1 基础流转测试

| 场景 | 输入 | 预期路径 |
|------|------|----------|
| 新建故事 | Initialize 模式 | Initialize → Planner → Writer → Reviewer → Memory → End |
| 续写故事 | Continue 模式 | Load Memory → Planner → Writer → Reviewer → Memory → Waiting |

### 3.2 重试流程测试

| 场景 | 触发条件 | 预期行为 |
|------|----------|----------|
| 首次审查失败 | `is_valid=False` | retry_count++ → 回到 Writer |
| 达到重试上限 | `retry_count=5` | 进入兜底判断 |

### 3.3 兜底机制测试

| 场景 | 条件 | 预期路径 |
|------|------|----------|
| 低比例兜底 | `retry=5, ratio=3%` | Annotate & Pass → Memory |
| 高比例首次调整 | `retry=5, ratio=10%, adjust=0` | Planner Adjust → Planner |
| 高比例二次调整 | `retry=5, ratio=10%, adjust=1` | Planner Adjust → Planner |
| 强制标注 | `retry=5, ratio=10%, adjust=2` | Force Annotate → Memory |

### 3.4 断点续写测试

| 步骤 | 操作 | 验证点 |
|------|------|--------|
| 1 | 创建故事，生成第1集 | 数据库保存状态 |
| 2 | 模拟用户离线 | - |
| 3 | 使用 Continue 模式恢复 | Load Memory 正确恢复状态 |
| 4 | 生成第2集 | 状态正确更新 |

### 3.5 并发测试

| 场景 | 验证点 |
|------|--------|
| 多用户同时创建故事 | user_id 隔离正确 |
| 同用户多会话 | session_id 隔离正确 |
| 并发读写同一会话 | PostgreSQL 事务正确 |

---

## 4. 性能测试

### 4.1 指标

| 指标 | 目标值 | 测量方法 |
|------|--------|----------|
| 单集生成延迟 | < 30s | 端到端计时 |
| RAG 检索延迟 | < 100ms | Milvus 查询计时 |
| 数据库查询延迟 | < 50ms | PostgreSQL 查询计时 |
| 并发支持 | 10 用户 | 压力测试 |

### 4.2 瓶颈分析

潜在瓶颈：
- LLM 生成耗时
- Embedding 向量化耗时
- Milvus 检索延迟
- PostgreSQL 写入延迟

优化策略：
- 异步处理
- 批量操作
- 缓存热点数据

---

## 5. 错误处理

### 5.1 异常类型

| 异常 | 场景 | 处理方式 |
|------|------|----------|
| LLM API 超时 | 生成/审查 | 重试 + 降级 |
| Milvus 连接失败 | RAG 检索 | 跳过 RAG，直接生成 |
| PostgreSQL 连接失败 | 状态持久化 | 重试 + 报警 |
| 词汇表加载失败 | 词汇审查 | 使用缓存版本 |

### 5.2 降级策略

| 降级场景 | 策略 |
|----------|------|
| RAG 不可用 | 跳过风格参考，直接生成 |
| LLM 审查不可用 | 使用规则审查 |
| 数据库不可用 | 使用本地文件缓存 |

---

## 6. 监控与日志

### 6.1 关键指标

- Node 执行耗时
- 条件边分支统计
- 错误率
- 重试次数分布

### 6.2 日志规范

- 每个节点入口/出口记录
- 条件边决策记录
- 异常完整堆栈
- 用户请求 ID 追踪

---

## 7. 部署验证

### 7.1 预发布检查

- [ ] 所有测试通过
- [ ] 性能指标达标
- [ ] 错误处理覆盖
- [ ] 日志输出正确
- [ ] 监控告警配置

### 7.2 生产部署

1. 更新 Docker 镜像
2. 执行数据库迁移
3. 配置环境变量
4. 启动服务
5. 烟雾测试

### 7.3 回滚计划

- 保留上一版本镜像
- 数据库变更可逆
- 快速切换开关

---

## 8. 文件清单

| 文件 | 用途 |
|------|------|
| `src/graph/graph.py` | Graph 组装 |
| `src/main.py` | CLI 入口（更新） |
| `app.py` | Streamlit 入口（更新） |
| `tests/test_integration.py` | 集成测试 |
| `tests/test_e2e.py` | 端到端测试 |
| `scripts/load_test.py` | 性能测试 |
