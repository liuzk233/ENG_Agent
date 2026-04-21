# Phase 0: 基础设施部署

> 状态：✅ 已完成

---

## 1. 目标

搭建项目运行所需的基础设施，包括向量数据库（Milvus）和关系数据库（PostgreSQL）。

---

## 2. 服务清单

| 服务 | 端口 | 用途 |
|------|------|------|
| Milvus | 19530 | 向量存储与检索 |
| PostgreSQL | 5432 | 记忆持久化 |

---

## 3. Docker Compose 配置

### 3.1 文件位置

`docker-compose.yml`（项目根目录）

### 3.2 服务定义要点

**Milvus 依赖服务**：
- `etcd`：元数据存储
- `minio`：对象存储

**PostgreSQL 配置**：
- 镜像：`postgres:15-alpine`
- 数据卷：`postgres_data`
- 健康检查：`pg_isready`

### 3.3 环境变量

```
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=vocabweaver
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=vocabweaver_memory
```

---

## 4. PostgreSQL Schema

### 4.1 表结构

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `sessions` | 会话元信息 | `user_id`, `session_id`, `total_episodes`, `current_episode`, `style`, `status` |
| `story_bibles` | 故事圣经 | `session_id`, `content` (JSONB), `version` |
| `episode_states` | 集数状态快照 | `session_id`, `episode_num`, `state` (JSONB), `transcript` |
| `vocabulary_progress` | 词汇使用记录 | `session_id`, `word`, `occurrence_count`, `contexts` (JSONB) |

### 4.2 索引策略

- `idx_sessions_user`：按 `user_id` 查询
- `idx_sessions_status`：按 `status` 过滤
- `idx_episodes_session`：按 `session_id` 查询集数状态
- `idx_vocab_session`：按 `session_id` 查询词汇进度

### 4.3 触发器

- `update_updated_at()`：自动更新 `updated_at` 字段

---

## 5. 初始化脚本

### 5.1 文件位置

`init/init.sql`

### 5.2 执行顺序

1. 启用 `uuid-ossp` 扩展
2. 创建四张核心表
3. 创建索引
4. 创建触发器

---

## 6. 配置文件更新

### 6.1 config.py 新增项

```python
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "vocabweaver")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
POSTGRES_DB = os.getenv("POSTGRES_DB", "vocabweaver_memory")
POSTGRES_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
```

### 6.2 requirements.txt 新增项

```
psycopg2-binary>=2.9.0
# 或 asyncpg (异步版本)
```

---

## 7. 验证步骤

1. 启动服务：`docker-compose up -d`
2. 检查 Milvus：`curl http://localhost:19530/v1/vector/collections`
3. 检查 PostgreSQL：`psql -h localhost -U vocabweaver -d vocabweaver_memory -c "\dt"`
4. 验证表结构：确认四张表已创建

---

## 8. 文件清单

| 文件 | 用途 |
|------|------|
| `docker-compose.yml` | 服务编排 |
| `init/init.sql` | 数据库初始化 |
| `.env` | 环境变量 |
| `src/utils/config.py` | 配置读取 |
