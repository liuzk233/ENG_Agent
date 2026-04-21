# Phase 2: 数据源头清洗与灌库

> 状态：✅ 已完成

---

## 1. 目标

将 Markdown 语料处理后灌入 Milvus 向量数据库，支持词汇软过滤检索。

---

## 2. 数据流

```
data/raw/corpus/          # 原始文件（只读）
      ↓
data/processed/markdown/  # Markdown 文件
      ↓
[切片 + 词汇审查]
      ↓
[Embedding 向量化]
      ↓
Milvus (HNSW + Trie)
```

---

## 3. Markdown 切片器

### 3.1 文件位置

`src/rag/builder.py`

### 3.2 切片策略

- 按标题层级切片（`#`, `##`, `###`）
- 保留标题层级上下文为 metadata
- 计算词数（`word_count`）

### 3.3 Metadata 字段

| 字段 | 来源 | 示例 |
|------|------|------|
| `source` | 文件路径 | `data/processed/markdown/exam_paper/ch1.md` |
| `category` | 父目录名 | `exam_paper` |
| `genre` | 父目录名（默认） | `exam_paper` |
| `h1` | 一级标题 | `Chapter 1` |
| `h2` | 二级标题 | `Introduction` |
| `word_count` | 词数统计 | `256` |

---

## 4. 词汇软过滤

### 4.1 设计原则

**软过滤 vs 硬过滤**：
- 硬过滤：删除含超纲词的切片 ❌ 数据丢失
- 软过滤：打标记，保留所有数据 ✅ 灵活检索

### 4.2 审查字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_vocabulary_clean` | bool | 是否通过词汇审查 |
| `out_of_scope_words` | str | 超纲词列表（逗号分隔） |

### 4.3 审查流程

1. 判断英文文本（英文字符占比 > 50%）
2. 调用 `check_vocabulary()` 函数
3. 解析 feedback 提取超纲词
4. UTF-8 字节级截断（限制 500 字节）

---

## 5. Milvus Schema

### 5.1 Collection 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | VARCHAR(64) | 主键（MD5） |
| `text` | VARCHAR(65535) | 切片文本 |
| `embedding` | FLOAT_VECTOR(1024) | 向量 |
| `source` | VARCHAR(512) | 来源文件 |
| `genre` | VARCHAR(64) | 体裁 |
| `category` | VARCHAR(128) | 分类 |
| `file_name` | VARCHAR(256) | 文件名 |
| `h1` | VARCHAR(256) | 一级标题 |
| `h2` | VARCHAR(256) | 二级标题 |
| `word_count` | INT64 | 词数 |
| `is_vocabulary_clean` | BOOL | 词汇审查结果 |
| `out_of_scope_words` | VARCHAR(512) | 超纲词列表 |

### 5.2 索引策略

| 字段 | 索引类型 | 参数 |
|------|----------|------|
| `embedding` | HNSW | `M=16, efConstruction=256, COSINE` |
| `genre` | Trie | - |
| `category` | Trie | - |
| `source` | Trie | - |

---

## 6. Embedder 工厂模式

### 6.1 文件位置

`src/rag/embedder.py`

### 6.2 后端切换

| 后端 | 环境变量 | 特点 |
|------|----------|------|
| DashScope | `EMBEDDING_BACKEND=dashscope` | 云端 API，按 Token 计费 |
| BGE-M3 | `EMBEDDING_BACKEND=bge-m3` | 本地 GPU，固定成本 |

### 6.3 配置差异

| 维度 | DashScope | BGE-M3 |
|------|-----------|--------|
| Latency | 网络往返 | 纯计算 |
| Cost | 按 Token | GPU 电费 |
| 运维 | 零运维 | 管理 GPU |
| batch_size | 32 | 8（显存限制） |

---

## 7. 检索器

### 7.1 文件位置

`src/rag/retriever.py`

### 7.2 检索参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `top_k` | 5 | 返回结果数 |
| `relevance_threshold` | 0.75 | 相似度阈值 |
| `strict_vocabulary` | True | 是否只返回纯净语料 |

### 7.3 过滤表达式构建

支持条件：
- `style` → `category == "{style}"`
- `genre` → `genre == "{genre}"`
- `min_word_count` → `word_count >= {n}`
- `max_word_count` → `word_count <= {n}`
- `strict_vocabulary=True` → `is_vocabulary_clean == true`

### 7.4 语义门控

- 目标词 < 2 个时跳过检索
- 避免单词查询效果不佳

---

## 8. 验证结果

### 8.1 数据统计

- Markdown 文件：12 个
- 切片总数：4689 条
- 纯净语料：2070 条（44%）
- 含超纲词语料：2619 条（56%）

### 8.2 检索测试

- 严格模式：只返回 `is_vocabulary_clean == true`
- 宽松模式：返回所有相关切片

---

## 9. 文件清单

| 文件 | 用途 |
|------|------|
| `src/rag/__init__.py` | 模块导出 |
| `src/rag/builder.py` | 知识库构建 |
| `src/rag/embedder.py` | Embedder 工厂 |
| `src/rag/retriever.py` | Milvus 检索器 |
| `scripts/test_milvus_bge_m3.py` | 集成测试 |
