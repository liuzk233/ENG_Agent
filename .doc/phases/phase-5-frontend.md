# Phase 5: 前端交互页面实现

## 概述

为 VocabWeaver 项目创建专业的前端交互页面，采用 **FastAPI + React + WebSocket** 技术栈，实现真实时进度反馈、响应式布局和前后端分离架构。

---

## 1. 现状与痛点

### 1.1 当前架构

```
Streamlit (app.py)
    ↓ compiled_graph.invoke() [同步阻塞]
LangGraph
    ↓ initialize → planner → writer → reviewer → memory
PostgreSQL + Milvus
```

### 1.2 核心痛点

| 痛点 | 根因 | 影响 |
|------|------|------|
| 同步阻塞 | `invoke()` 是同步调用 | 用户等待无反馈 |
| 无实时进度 | 无事件回调机制 | 无法展示节点状态 |
| 移动端适配差 | Streamlit 不支持响应式 | 手机端体验不佳 |
| 无 API 层 | 前端直接调用 Graph | 无法扩展多客户端 |

---

## 2. 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite + TypeScript)                       │
│  - Zustand 状态管理                                          │
│  - Ant Design 组件库                                         │
│  - WebSocket 实时通信                                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ WebSocket / REST API
┌──────────────────────────▼──────────────────────────────────┐
│  Backend (FastAPI)                                          │
│  - /api/sessions (会话管理)                                  │
│  - /api/history (历史记录)                                   │
│  - /ws/generate (WebSocket 实时生成)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │ astream()
┌──────────────────────────▼──────────────────────────────────┐
│  LangGraph Core (现有代码)                                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  Data Layer: PostgreSQL + Milvus                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 项目结构

```
vocabweaver/
├── backend/                          # 后端服务
│   ├── app/
│   │   ├── main.py                   # FastAPI 入口
│   │   ├── config.py                 # 配置管理
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── sessions.py       # 会话 API
│   │   │   │   └── history.py        # 历史 API
│   │   │   └── websocket.py          # WebSocket 处理
│   │   ├── services/
│   │   │   └── graph_service.py      # LangGraph 封装
│   │   └── models/
│   │       └── schemas.py            # Pydantic 模型
│   └── requirements.txt
│
├── frontend/                         # 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout/               # 布局组件
│   │   │   ├── Generator/            # 生成页面组件
│   │   │   └── History/              # 历史页面组件
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts       # WebSocket hook
│   │   │   └── useGeneration.ts      # 生成流程 hook
│   │   ├── stores/
│   │   │   └── sessionStore.ts       # Zustand store
│   │   └── types/
│   │       └── index.ts              # TypeScript 类型
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml
└── nginx.conf
```

---

## 4. API 设计

### 4.1 REST API 端点

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | /api/sessions | 创建新会话 |
| GET | /api/sessions/{session_id} | 获取会话状态 |
| DELETE | /api/sessions/{session_id} | 删除会话 |
| GET | /api/users/{user_id}/sessions | 获取用户会话列表 |
| GET | /api/sessions/{session_id}/episodes | 获取集数列表 |

### 4.2 WebSocket 消息协议

**客户端 → 服务端**:
- `start`: 开始生成，携带 target_words、style、total_episodes
- `continue`: 续写，携带新的 target_words
- `cancel`: 取消生成

**服务端 → 客户端**:
- `node_start`: 节点开始执行
- `node_end`: 节点执行完成，携带节点名称、状态、输出数据
- `complete`: 整体生成完成
- `error`: 发生错误

---

## 5. 实施步骤

### Phase 5.1: API 层搭建（1 周）

#### 5.1.1 创建 FastAPI 项目骨架

| 任务 | 说明 |
|------|------|
| 创建 `backend/` 目录结构 | 按上述项目结构创建 |
| 初始化 FastAPI 应用 | main.py 入口、CORS 配置 |
| 配置管理迁移 | 从 `src/utils/config.py` 迁移到 `backend/app/config.py` |

#### 5.1.2 实现 REST API

| 任务 | 说明 |
|------|------|
| 会话管理 API | 创建、查询、删除会话 |
| 历史记录 API | 用户会话列表、集数列表 |
| Pydantic 模型定义 | 请求/响应数据结构 |

#### 5.1.3 实现 WebSocket 端点

| 任务 | 说明 |
|------|------|
| 连接管理器 | 管理活跃 WebSocket 连接 |
| 消息解析 | 解析客户端消息类型 |
| 错误处理 | 异常捕获与错误消息推送 |

#### 5.1.4 LangGraph astream 改造

| 任务 | 说明 |
|------|------|
| 将 `invoke()` 改为 `astream()` | 支持异步流式执行 |
| 节点事件封装 | 封装 node_start/node_end 事件 |
| 状态提取 | 从事件中提取关键状态字段 |

---

### Phase 5.2: 前端开发（2 周）

#### 5.2.1 项目初始化

| 任务 | 说明 |
|------|------|
| 创建 Vite + React + TypeScript 项目 | `npm create vite@latest` |
| 安装依赖 | antd, zustand, axios, tailwindcss |
| 配置 Tailwind CSS | tailwind.config.js, postcss.config.js |
| 配置路径别名 | vite.config.ts 中设置 @ 别名 |

#### 5.2.2 核心组件开发

| 组件 | 功能 |
|------|------|
| Layout/Header | 顶部导航栏 |
| Layout/Sidebar | 侧边栏（历史会话列表） |
| Generator/WordInput | 词汇输入框（支持逗号分隔） |
| Generator/StyleSelect | 风格选择下拉框 |
| Generator/ProgressPanel | 进度面板（显示节点状态） |
| Generator/ResultDisplay | 结果展示（文章内容、超纲词警告） |
| History/SessionList | 历史会话列表 |

#### 5.2.3 状态管理

| 任务 | 说明 |
|------|------|
| Zustand store 设计 | sessionStore 管理会话状态、生成结果 |
| WebSocket 消息处理 | 根据消息类型更新 store |
| 持久化配置 | localStorage 保存用户偏好 |

#### 5.2.4 WebSocket Hook 封装

| 功能 | 说明 |
|------|------|
| 连接管理 | 建立/断开连接 |
| 消息收发 | 发送 start/continue/cancel 消息 |
| 重连机制 | 断线自动重连 |
| 心跳检测 | 保持连接活跃 |

#### 5.2.5 响应式布局

| 任务 | 说明 |
|------|------|
| 移动端适配 | 侧边栏折叠、表单响应式 |
| 断点设计 | 适配手机、平板、桌面 |

---

### Phase 5.3: 集成测试（1 周）

#### 5.3.1 功能测试

| 测试项 | 说明 |
|------|------|
| WebSocket 连接测试 | 连接建立、断开、重连 |
| 流式生成测试 | 验证节点事件正确推送 |
| 多集续写测试 | Continue 模式正常工作 |
| 取消操作测试 | 中途取消正常响应 |

#### 5.3.2 并发测试

| 测试项 | 说明 |
|------|------|
| 多用户同时生成 | 验证会话隔离 |
| 连接数限制 | 测试最大并发连接数 |

#### 5.3.3 兼容性测试

| 测试项 | 说明 |
|------|------|
| 浏览器兼容 | Chrome, Firefox, Safari, Edge |
| 移动端测试 | iOS Safari, Android Chrome |

---

### Phase 5.4: 部署上线（0.5 周）

#### 5.4.1 Docker 化

| 任务 | 说明 |
|------|------|
| 后端 Dockerfile | Python 镜像，安装依赖 |
| 前端 Dockerfile | Node 镜像，构建静态文件 |
| docker-compose 更新 | 添加 frontend, nginx 服务 |

#### 5.4.2 Nginx 配置

| 任务 | 说明 |
|------|------|
| 反向代理 | 代理前端和后端 API |
| WebSocket 代理 | 支持 WebSocket 连接 |
| SSL 配置 | HTTPS 证书配置 |

#### 5.4.3 监控与日志

| 任务 | 说明 |
|------|------|
| 日志收集 | 后端日志配置 |
| 性能监控 | 响应时间、错误率监控 |

---

## 6. 文件变更清单

### 新增文件

| 文件 | 用途 |
|------|------|
| `backend/app/main.py` | FastAPI 入口 |
| `backend/app/config.py` | 配置管理 |
| `backend/app/api/websocket.py` | WebSocket 处理 |
| `backend/app/api/routes/sessions.py` | 会话 API |
| `backend/app/api/routes/history.py` | 历史 API |
| `backend/app/services/graph_service.py` | LangGraph 封装 |
| `backend/app/models/schemas.py` | Pydantic 模型 |
| `frontend/src/hooks/useWebSocket.ts` | WebSocket Hook |
| `frontend/src/stores/sessionStore.ts` | 状态管理 |
| `frontend/src/components/**/*.tsx` | UI 组件 |

### 修改文件

| 文件 | 变更 |
|------|------|
| `src/graph/graph.py` | 添加 astream 支持 |
| `src/requirements.txt` | 添加 fastapi, uvicorn, websockets |
| `docker-compose.yml` | 添加前端服务 |
| `CLAUDE.md` | 更新项目结构 |

---

## 7. 依赖新增

### 后端

| 依赖 | 用途 |
|------|------|
| fastapi | Web 框架 |
| uvicorn[standard] | ASGI 服务器 |
| websockets | WebSocket 支持 |
| python-multipart | 表单数据处理 |
| pydantic | 数据验证 |

### 前端

| 依赖 | 用途 |
|------|------|
| react | UI 框架 |
| antd | 组件库 |
| zustand | 状态管理 |
| axios | HTTP 客户端 |
| vite | 构建工具 |
| typescript | 类型支持 |
| tailwindcss | 样式框架 |

---

## 8. 验证方式

1. **API 测试**: `pytest tests/test_api.py`
2. **WebSocket 测试**: 使用 wscat 或 Postman WebSocket 测试工具
3. **前端测试**: `npm run dev` 启动开发服务器
4. **完整流程**:
   - 输入目标词汇 → 点击生成 → 实时看到节点状态
   - 验证超纲词警告显示
   - 验证多集续写功能
   - 移动端访问验证响应式布局

---

## 9. 时间估算

| Phase | 任务 | 预估时间 |
|-------|------|----------|
| 5.1 | API 层搭建 | 1 周 |
| 5.2 | 前端开发 | 2 周 |
| 5.3 | 集成测试 | 1 周 |
| 5.4 | 部署上线 | 0.5 周 |
| **总计** | | **4.5 周** |

---

## 10. 状态

- [x] Phase 5 规划完成
- [x] Phase 5.1: API 层搭建
- [x] Phase 5.2: 前端开发
- [x] Phase 5.3: 集成测试
- [x] Phase 5.4: 部署上线
  - [x] 5.4.1 Docker 化
  - [x] 5.4.2 Nginx 配置
  - [x] 5.4.3 监控与日志

### 测试结果

| 测试类型 | 数量 | 状态 |
|----------|------|------|
| API 端点测试 | 12 | 通过 |
| 流式生成测试 | 6 | 通过 |
| 集成测试 | 37 | 通过 |
| Graph 流转测试 | 15 | 通过 |
| 端到端测试 | 12 | 通过 |
| **总计** | **82** | **全部通过** |
