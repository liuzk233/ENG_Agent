# VocabWeaver 前端测试文档

## 测试环境

- 前端地址: http://localhost:5173
- 后端地址: http://localhost:8001
- 测试工具: playwright-cli
- 浏览器: Chrome (headed mode)

## 测试前准备

```bash
# 1. 启动后端服务
cd D:\0_workspace\1_project\10_Eng_agent\ENG_Agent
set PYTHONPATH=D:\0_workspace\1_project\10_Eng_agent\ENG_Agent\src;D:\0_workspace\1_project\10_Eng_agent\ENG_Agent\backend
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001

# 2. 启动前端服务
cd frontend
npm run dev

# 3. 启动 Docker 服务 (Milvus + PostgreSQL)
docker-compose up -d
```

---

## 测试用例 1: 初始化 → 大纲规划 → 内容生成 → 词汇审查 → 状态保存 流程验证

### 目的
验证后端 LangGraph 流程各节点完成后，前端进度面板对应的图标能正确亮起。

### 前置条件
- 后端服务正常运行
- 前端服务正常运行
- WebSocket 连接正常

### 测试步骤

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 打开页面 `http://localhost:5173` | 页面正常加载 |
| 2 | 输入目标词汇: `adventure, explore` | 显示"已选择 2 个单词" |
| 3 | 点击"开始生成" | 显示进度面板 |
| 4 | 观察节点状态变化 | 各节点依次亮起 |

### 节点状态说明

| 节点 | 后端函数 | 前端显示名称 | 图标状态 |
|------|----------|--------------|----------|
| initialize | `initialize_node` | 初始化 | 灰色(待处理) → 蓝色旋转(运行中) → 绿色勾(完成) |
| planner | `planner_node` | 大纲规划 | 灰色 → 蓝色 → 绿色 |
| writer | `writer_node` | 内容生成 | 灰色 → 蓝色 → 绿色 |
| reviewer | `reviewer_node` | 词汇审查 | 灰色 → 蓝色 → 绿色 |
| memory | `memory_node` | 状态保存 | 灰色 → 蓝色 → 绿色 |

### playwright-cli 命令

```bash
# 打开浏览器
playwright-cli open http://localhost:5173 --headed

# 输入词汇
playwright-cli fill e45 "adventure, explore" --submit

# 开始生成
playwright-cli snapshot
playwright-cli click e83

# 立即获取进度面板快照（初始化阶段）
playwright-cli snapshot

# 等待 2 秒后获取快照（大纲规划/内容生成阶段）
sleep 2
playwright-cli snapshot

# 等待 5 秒后获取快照（内容生成/词汇审查阶段）
sleep 3
playwright-cli snapshot

# 等待 10 秒后获取快照（词汇审查/状态保存阶段）
sleep 5
playwright-cli snapshot

# 等待完成后获取最终快照
sleep 20
playwright-cli snapshot

# 查看控制台日志确认节点完成事件
playwright-cli console

# 关闭浏览器
playwright-cli close
```

### 验证点

- [ ] **初始化节点**: 点击生成后立即显示蓝色旋转图标，完成后变为绿色勾
- [ ] **大纲规划节点**: 初始化完成后自动亮起蓝色，完成后变绿色
- [ ] **内容生成节点**: 大纲规划完成后亮起，完成后变绿色（耗时最长）
- [ ] **词汇审查节点**: 内容生成完成后亮起，完成后变绿色
- [ ] **状态保存节点**: 词汇审查通过后亮起，完成后变绿色
- [ ] 所有节点完成后，进度面板消失，显示结果面板

### 控制台日志验证

正常流程应看到以下日志顺序：

```
[WebSocket] 收到消息: node_start {type: node_start, payload: {node: initialize}}
[Generation] 收到消息: node_start
[WebSocket] 收到消息: node_end {type: node_end, payload: {node: initialize, status: success}}
[Generation] 收到消息: node_end
[WebSocket] 收到消息: node_end {type: node_end, payload: {node: planner, status: success}}
[Generation] 收到消息: node_end
[WebSocket] 收到消息: node_end {type: node_end, payload: {node: writer, status: success}}
[Generation] 收到消息: node_end
[WebSocket] 收到消息: node_end {type: node_end, payload: {node: reviewer, status: success}}
[Generation] 收到消息: node_end
[WebSocket] 收到消息: node_end {type: node_end, payload: {node: memory, status: success}}
[Generation] 收到消息: node_end
[WebSocket] 收到消息: complete {type: complete, payload: {...}}
[Generation] 收到消息: complete
```

---

## 测试用例 2: 点击历史会话恢复

### 目的
验证用户可以从历史会话列表中恢复之前的会话状态。

### 前置条件
- 已完成至少一次文章生成
- 历史会话列表中有记录

### 测试步骤

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 打开页面 `http://localhost:5173` | 页面正常加载，显示历史会话列表 |
| 2 | 查看侧边栏历史会话列表 | 显示之前生成的会话记录 |
| 3 | 点击任意历史会话 | 页面跳转/加载该会话的状态 |
| 4 | 检查会话信息 | 显示正确的集数、风格、目标词汇 |

### playwright-cli 命令

```bash
# 打开浏览器
playwright-cli open http://localhost:5173 --headed

# 获取页面快照
playwright-cli snapshot

# 点击历史会话（假设第一个会话的 ref 是 e181）
playwright-cli click e181

# 确认加载成功
playwright-cli snapshot

# 关闭浏览器
playwright-cli close
```

### 验证点
- [ ] 历史会话列表正确显示
- [ ] 点击会话后页面状态正确更新
- [ ] 会话详情（集数、风格）正确显示

---

## 测试用例 3: 多集数生成

### 目的
验证系统可以正确生成多集故事，并维护故事连贯性。

### 前置条件
- 后端服务正常运行
- 前端服务正常运行

### 测试步骤

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 打开页面 | 页面正常加载 |
| 2 | 输入目标词汇: `adventure, mystery` | 显示"已选择 2 个单词" |
| 3 | 选择风格: "冒险故事" | 下拉框显示选中值 |
| 4 | 设置总集数: 3 | 输入框显示 "3" |
| 5 | 点击"开始生成" | 显示进度面板，节点状态更新 |
| 6 | 等待第一集完成 | 显示"第 1/3 集" |
| 7 | 等待全部完成 | 显示"第 3/3 集"，生成结果正确 |

### playwright-cli 命令

```bash
# 打开浏览器
playwright-cli open http://localhost:5173 --headed

# 输入词汇
playwright-cli fill e45 "adventure, mystery" --submit

# 设置集数为 3
playwright-cli click e69    # 增加
playwright-cli click e69    # 增加

# 确认集数为 3
playwright-cli snapshot

# 开始生成
playwright-cli click e83

# 等待生成完成
sleep 60

# 检查结果
playwright-cli snapshot
playwright-cli console

# 关闭浏览器
playwright-cli close
```

### 验证点
- [ ] 集数选择器正常工作
- [ ] 进度面板显示正确的集数进度
- [ ] 多集故事连贯性（后续集数继承前文）
- [ ] 最终集数显示正确

---

## 测试用例 4: 不同风格选择

### 目的
验证系统支持多种文章风格，并能正确应用到生成内容。

### 测试步骤

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 打开页面 | 页面正常加载 |
| 2 | 输入目标词汇: `explore, discover` | 显示"已选择 2 个单词" |
| 3 | 点击风格下拉框 | 显示风格选项列表 |
| 4 | 选择不同风格并生成 | 每种风格生成内容风格不同 |

### 可用风格选项

| 风格值 | 显示名称 | 预期特点 |
|--------|----------|----------|
| adventure | 冒险故事 | 激烈、探险、勇敢 |
| scifi | 科幻小说 | 未来、科技、想象 |
| mystery | 悬疑推理 | 悬念、解谜、推理 |
| news | 新闻报道 | 客观、正式、简洁 |
| exam_paper | 考试范文 | 规范、教育性、标准化 |

### playwright-cli 命令

```bash
# 打开浏览器
playwright-cli open http://localhost:5173 --headed

# 输入词汇
playwright-cli fill e45 "explore, discover" --submit

# 点击风格选择器
playwright-cli click e63

# 获取下拉选项快照
playwright-cli snapshot

# 选择不同风格（根据实际 ref 点击）
playwright-cli click "getByText('科幻小说')"

# 开始生成
playwright-cli click e83

# 等待并检查结果
sleep 30
playwright-cli snapshot

# 关闭浏览器
playwright-cli close
```

### 验证点
- [ ] 下拉框展开/收起正常
- [ ] 风格选项完整显示
- [ ] 选择后下拉框显示正确值
- [ ] 生成内容风格与选择匹配

---

## 测试用例 5: 错误处理测试

### 目的
验证系统在异常情况下的错误处理和用户提示。

### 测试子场景

#### 5.1 空词汇提交

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 不输入任何词汇 | "已选择 0 个单词" |
| 2 | 点击"开始生成"按钮 | 按钮禁用，无法点击 |

**验证点**: 按钮应保持 disabled 状态

#### 5.2 后端服务不可用

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 停止后端服务 | - |
| 2 | 输入词汇并点击生成 | 显示连接错误提示 |
| 3 | 检查控制台日志 | 显示 WebSocket 连接失败 |

```bash
# 停止后端
# (手动停止后端进程)

# 测试连接失败
playwright-cli open http://localhost:5173 --headed
playwright-cli fill e45 "test" --submit
playwright-cli click e83
sleep 5
playwright-cli console
```

#### 5.3 超纲词汇处理

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 输入超纲词汇作为目标词 | 词汇被接受 |
| 2 | 生成文章 | 可能显示"兜底模式"标签 |
| 3 | 检查超纲词警告 | 如有超纲词，显示警告标签 |

#### 5.4 网络超时处理

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 正常开始生成 | 进度面板显示 |
| 2 | 模拟网络中断 | - |
| 3 | 检查重连机制 | 自动重连或显示错误 |

### 验证点
- [ ] 空词汇时按钮禁用
- [ ] 后端不可用时显示友好错误
- [ ] 超纲词警告正确显示
- [ ] 网络错误有重试机制

---

## 测试用例 6: 历史对话删除

### 目的
验证用户可以删除历史会话记录。

### 测试步骤

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 打开页面，确认有历史会话 | 列表显示会话记录 |
| 2 | 将鼠标悬停在会话项上 | 显示删除按钮或操作菜单 |
| 3 | 点击删除按钮 | 弹出确认对话框（如有） |
| 4 | 确认删除 | 会话从列表中移除 |
| 5 | 刷新页面 | 会话不再出现 |

### playwright-cli 命令

```bash
# 打开浏览器
playwright-cli open http://localhost:5173 --headed

# 获取当前会话列表
playwright-cli snapshot

# 悬停在会话项上（触发删除按钮）
playwright-cli hover e181

# 获取快照查看删除按钮
playwright-cli snapshot

# 如果有删除按钮，点击它
# playwright-cli click <delete_button_ref>

# 确认删除
# playwright-cli click <confirm_button_ref>

# 验证会话已删除
playwright-cli snapshot

playwright-cli close
```

### 验证点
- [ ] 悬停显示删除按钮
- [ ] 删除确认对话框正确显示
- [ ] 删除后会话从列表移除
- [ ] 刷新后会话不再出现

---

## 测试执行命令汇总

```bash
# 一键启动测试环境
cd D:\0_workspace\1_project\10_Eng_agent\ENG_Agent

# 启动 Docker 服务
docker-compose up -d

# 启动后端（新终端）
set PYTHONPATH=D:\0_workspace\1_project\10_Eng_agent\ENG_Agent\src;D:\0_workspace\1_project\10_Eng_agent\ENG_Agent\backend
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001

# 启动前端（新终端）
cd frontend && npm run dev

# 执行测试（新终端）
playwright-cli open http://localhost:5173 --headed
```

---

## 测试结果记录模板

| 测试用例 | 执行日期 | 执行人 | 结果 | 备注 |
|----------|----------|--------|------|------|
| TC1: 流程节点图标验证 | | | PASS/FAIL | |
| TC2: 历史会话恢复 | | | PASS/FAIL | |
| TC3: 多集数生成 | | | PASS/FAIL | |
| TC4: 不同风格选择 | | | PASS/FAIL | |
| TC5: 错误处理 | | | PASS/FAIL | |
| TC6: 历史对话删除 | | | PASS/FAIL | |

---

## 已知问题

| 问题描述 | 严重程度 | 状态 | 修复日期 |
|----------|----------|------|----------|
| 集数显示从 2 开始 | High | 已修复 | 2026-04-23 |
| WebSocket 连接时序问题 | High | 已修复 | 2026-04-23 |
| React Strict Mode 双重渲染 | Medium | 已修复 | 2026-04-23 |

---

## 附录: playwright-cli 常用命令

```bash
# 基本操作
playwright-cli open <url>              # 打开页面
playwright-cli close                   # 关闭浏览器
playwright-cli snapshot                # 获取页面快照
playwright-cli screenshot              # 截图

# 交互操作
playwright-cli click <ref>             # 点击元素
playwright-cli fill <ref> "text"       # 填充输入框
playwright-cli type "text"             # 输入文本
playwright-cli press Enter             # 按键
playwright-cli hover <ref>             # 悬停

# 调试操作
playwright-cli console                 # 查看控制台日志
playwright-cli console error           # 只看错误日志
playwright-cli network                 # 查看网络请求

# 高级操作
playwright-cli eval "document.title"   # 执行 JavaScript
playwright-cli wait-for "selector"     # 等待元素出现
```
