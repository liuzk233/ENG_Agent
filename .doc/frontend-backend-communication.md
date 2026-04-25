# VocabWeaver 前后端通信流程

## 一、通信架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   App.tsx   │───>│useGeneration│───>│   useWebSocket      │  │
│  │  (UI 组件)   │    │  (业务逻辑)  │    │  (WebSocket 管理)    │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│                            │                    │                │
│                            ▼                    ▼                │
│                    ┌─────────────┐    ┌─────────────┐           │
│                    │sessionStore │    │ WebSocket   │           │
│                    │  (Zustand)  │    │ Connection  │           │
│                    └─────────────┘    └─────────────┘           │
└───────────────────────────────────────┬─────────────────────────┘
                                        │ WebSocket
                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │ websocket.py    │───>│ graph_service   │───>│  LangGraph  │  │
│  │ (WebSocket 端点) │    │  (流程封装)      │    │  (生成引擎)  │  │
│  └─────────────────┘    └─────────────────┘    └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、详细通信流程

### 阶段 1: 用户点击"开始生成"

```
App.tsx::handleStart()
    │
    ├── 1. 检查 targetWords.length > 0
    │
    └── 2. 调用 startGeneration(targetWords, style, totalEpisodes)
                │
                ▼
        useGeneration.ts::startGeneration()
            │
            ├── 1. 生成 newSessionId = `session_${Date.now()}_${random}`
            │
            ├── 2. 创建 payload = { userId, targetWords, style, totalEpisodes }
            │
            ├── 3. 设置 pendingMessageRef.current = { type: 'start', payload }
            │       ⚠️ 关键：消息暂存，等待连接
            │
            ├── 4. 调用 setSessionId(newSessionId)
            │       → 触发 useWebSocket 的 useEffect
            │
            └── 5. 调用 start(episodes)
                    → 更新 Zustand store: isGenerating=true, 初始化节点状态
```

### 阶段 2: WebSocket 连接建立

```
useWebSocket.ts (useEffect 监听 sessionId)
    │
    ├── sessionId 变化 (从 null → "session_xxx")
    │
    ├── 调用 connect()
    │       │
    │       ├── 构造 wsUrl = `ws://${window.location.host}/ws/generate/${sessionId}`
    │       │
    │       └── 创建 WebSocket 实例
    │               │
    │               ├── ws.onopen → setIsConnected(true)
    │               │       → 调用 onConnectRef.current()
    │               │
    │               ├── ws.onmessage → 解析消息 → 调用 onMessageRef.current(message)
    │               │
    │               ├── ws.onclose → setIsConnected(false)
    │               │
    │               └── ws.onerror → 打印错误
    │
    └── 返回清理函数 disconnect()
```

### 阶段 3: 发送生成请求

```
useGeneration.ts (useEffect 监听 isConnected)
    │
    ├── isConnected 变化 (false → true)
    │
    ├── 检查 pendingMessageRef.current 是否存在
    │
    └── 发送消息: sendStart(pending.payload)
            │
            ▼
        useWebSocket.ts::sendStart()
            │
            ├── 检查 wsRef.current?.readyState === WebSocket.OPEN
            │
            └── 发送 JSON: { type: 'start', payload: {...} }
                    │
                    ▼
                WebSocket → 后端
```

### 阶段 4: 后端处理

```
backend/app/api/websocket.py::websocket_generate()
    │
    ├── 接收消息: { type: 'start', payload: {...} }
    │
    ├── 调用 run_generation(session_id, payload, websocket)
    │       │
    │       ├── 创建 initial_state
    │       │
    │       ├── 调用 run_initialize_stream()
    │       │       │
    │       │       └── LangGraph astream() 流式执行
    │       │               │
    │       │               ├── initialize_node → 推送 node_end
    │       │               ├── planner_node → 推送 node_end
    │       │               ├── writer_node → 推送 node_end
    │       │               ├── reviewer_node → 推送 node_end
    │       │               └── memory_node → 推送 node_end
    │       │
    │       └── 推送 complete 消息
    │
    └── 消息格式 (后端使用 snake_case):
            {
              "type": "node_end",
              "payload": {
                "node": "writer",
                "status": "success",
                "data": {
                  "retry_count": 0,
                  "out_of_scope_words": [],
                  "draft_text": "..."
                }
              }
            }
            {
              "type": "complete",
              "payload": {
                "session_id": "session_xxx",
                "current_episode": 2,
                "final_text": "生成的文章...",
                "out_of_scope_words": [],
                "retry_count": 0,
                "fallback_mode": false
              }
            }
```

### 阶段 5: 前端接收消息

```
useWebSocket.ts::ws.onmessage()
    │
    ├── 解析 JSON: message = JSON.parse(event.data)
    │
    └── 调用 onMessageRef.current(message)
            │
            ▼
        useGeneration.ts::handleWebSocketMessage()
            │
            ├── switch(message.type)
            │
            ├── case 'node_start':
            │       → updateNode(node, 'running')
            │       → 更新 UI: 显示当前节点运行中
            │
            ├── case 'node_end':
            │       → updateNode(node, status, data)
            │       → 更新 UI: 显示节点完成状态
            │       ⚠️ 注意: 后端用 snake_case，前端需要转换
            │
            ├── case 'complete':
            │       → setResult(payload) → isGenerating=false
            │       → 保存会话到 store
            │       → UI 显示结果
            │
            └── case 'error':
                    → setError(message) → 显示错误
```

---

## 三、关键文件和行号

| 文件 | 关键函数/位置 | 作用 |
|------|--------------|------|
| `frontend/src/App.tsx:33` | `handleStart()` | 用户点击触发 |
| `frontend/src/hooks/useGeneration.ts:144` | `startGeneration()` | 业务逻辑入口 |
| `frontend/src/hooks/useGeneration.ts:127-141` | `useEffect(isConnected)` | 发送待发消息 |
| `frontend/src/hooks/useWebSocket.ts:67-124` | `connect()` | 建立 WebSocket |
| `frontend/src/hooks/useWebSocket.ts:87-95` | `ws.onmessage` | 接收消息 |
| `backend/app/api/websocket.py:127-236` | `run_generation()` | 后端处理流程 |

---

## 四、常见问题排查

### 问题 1: 进度条直接到 100%，无文章生成

**排查步骤:**

1. **检查浏览器 Console**
   ```
   F12 → Console 面板
   查找以下日志:
   - "[WebSocket] 正在连接:" → WebSocket URL 是否正确
   - "[WebSocket] 连接成功:" → 连接是否建立
   - "[WebSocket] 发送消息:" → 消息是否发送
   - "[WebSocket] 收到消息:" → 是否收到响应
   - "[Generation] 收到消息:" → 消息是否被处理
   ```

2. **检查 Network 面板**
   ```
   F12 → Network → WS (WebSocket)
   - 查看是否有 /ws/generate/ 请求
   - 点击请求查看 Messages 标签，确认发送和接收的消息
   ```

3. **检查后端日志**
   ```bash
   # 查看后端日志
   # 应该看到 "节点完成: xxx" 和 "生成完成: session=xxx"
   ```

### 问题 2: WebSocket 连接失败

**可能原因:**
- 后端未启动 (检查 localhost:8001/health)
- Vite 代理配置错误 (检查 vite.config.ts)
- 端口不匹配 (前端代理 8000 vs 后端实际 8001)

### 问题 3: 消息发送但无响应

**可能原因:**
- 后端处理超时 (LLM 调用耗时)
- LangGraph 执行出错 (检查后端日志)

### 问题 4: 收到消息但 UI 不更新

**可能原因:**
- 字段名不匹配 (后端 snake_case vs 前端 camelCase)
- Zustand store 更新问题
- React 重渲染问题

---

## 五、调试命令

### 测试后端 WebSocket 端点

```bash
# 使用 Python 测试 WebSocket
cd D:/0_workspace/1_project/10_Eng_agent/ENG_Agent
python -c "
import asyncio
import websockets
import json

async def test():
    uri = 'ws://localhost:8001/ws/generate/test123'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            'type': 'start',
            'payload': {
                'user_id': 'test',
                'target_words': ['test'],
                'style': 'adventure',
                'total_episodes': 1
            }
        }))
        for _ in range(10):
            msg = await ws.recv()
            print(json.loads(msg))

asyncio.run(test())
"
```

### 测试 Vite 代理

```bash
# 通过前端代理测试
python -c "
import asyncio
import websockets
import json

async def test():
    uri = 'ws://localhost:5173/ws/generate/test123'
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            'type': 'start',
            'payload': {
                'user_id': 'test',
                'target_words': ['test'],
                'style': 'adventure',
                'total_episodes': 1
            }
        }))
        for _ in range(10):
            msg = await ws.recv()
            print(json.loads(msg))

asyncio.run(test())
"
```

### 检查端口占用

```bash
# 检查后端端口
netstat -ano | findstr "8001"

# 检查前端端口
netstat -ano | findstr "5173"
```
