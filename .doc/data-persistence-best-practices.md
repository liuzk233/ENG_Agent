# Docker 数据持久化最佳实践

## 问题背景

在容器切换过程中，由于使用了匿名卷（Anonymous Volume），导致 Milvus 数据丢失。

---

## 三种 Docker 卷类型对比

| 类型 | 命名方式 | 生命周期 | 数据安全 |
|------|----------|----------|----------|
| **匿名卷** | 系统生成哈希 | 容器删除后孤立 | ❌ 易丢失 |
| **命名卷** | 用户指定名称 | 独立于容器 | ✅ 安全 |
| **绑定挂载** | 宿主机路径 | 独立于 Docker | ✅ 最安全 |

---

## 生产环境最佳实践

### 1. 使用命名卷（推荐）

```yaml
# docker-compose.yml
services:
  milvus:
    image: milvusdb/milvus:v2.4.14
    volumes:
      - milvus-data:/var/lib/milvus  # 命名卷

volumes:
  milvus-data:  # 显式声明命名卷
    name: vocabweaver-milvus-data  # 明确命名
```

**优点：**
- 数据独立于容器生命周期
- 易于备份和迁移
- 不会被误删

### 2. 使用绑定挂载（最安全）

```yaml
services:
  milvus:
    volumes:
      - ./data/milvus:/var/lib/milvus  # 宿主机路径
```

**优点：**
- 数据直接存储在宿主机
- 可以直接访问和备份
- 不依赖 Docker 卷管理

**缺点：**
- 跨平台路径问题（Windows/Linux/Mac）
- 需要手动管理权限

### 3. 定期备份

```bash
# 备份 Milvus 数据
docker run --rm \
  -v vocabweaver-milvus-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/milvus-$(date +%Y%m%d).tar.gz /data

# 恢复数据
docker run --rm \
  -v vocabweaver-milvus-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/milvus-20260422.tar.gz -C /
```

### 4. 数据卷标签约定

```yaml
volumes:
  milvus-data:
    name: ${PROJECT_NAME:-vocabweaver}-milvus-data
    labels:
      - "app=vocabweaver"
      - "component=milvus"
      - "backup=required"
```

---

## 本项目改进建议

### 当前配置（已修复）

```yaml
# docker-compose.yml - 使用命名卷
volumes:
  milvus-data:
    name: vocabweaver-milvus-data  # ✅ 显式命名
  postgres-data:
    name: vocabweaver-postgres-data
```

### 进一步改进：绑定挂载

```yaml
# docker-compose.yml - 使用绑定挂载
services:
  milvus:
    volumes:
      - ./data/docker/milvus:/var/lib/milvus

  postgres:
    volumes:
      - ./data/docker/postgres:/var/lib/postgresql/data
```

---

## 数据迁移清单

| 场景 | 操作 |
|------|------|
| 容器升级 | 命名卷自动保留 |
| 主机迁移 | 备份命名卷 → 复制 → 恢复 |
| 容灾恢复 | 从备份文件恢复 |
| 开发环境同步 | 使用绑定挂载 + Git |

---

## 总结

| 风险 | 预防措施 |
|------|----------|
| 容器误删 | ✅ 使用命名卷 |
| 数据丢失 | ✅ 定期备份 |
| 主机故障 | ✅ 异地备份 |
| 开发环境不一致 | ✅ 使用绑定挂载 |
