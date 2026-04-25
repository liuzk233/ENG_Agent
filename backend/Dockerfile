# ============================================
# VocabWeaver Backend Dockerfile
# ============================================
# 架构说明：
# - backend/ 作为 API 网关层
# - src/ 作为核心业务逻辑层
# - 通过 PYTHONPATH 让 backend 能导入 src 模块
# ============================================

FROM python:3.11-slim-bookworm AS backend

# ---------- Metadata ----------
LABEL maintainer="VocabWeaver Team"
LABEL version="1.0.0"
LABEL description="FastAPI backend with LangGraph multi-agent system"

# ---------- System Dependencies ----------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ---------- Workdir Setup ----------
WORKDIR /app

# ---------- Python Environment ----------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# 核心：设置 Python 模块搜索路径，解决 from src.xxx 导入问题
ENV PYTHONPATH="/app/src:/app/backend"

# ---------- Install Dependencies ----------
# 先复制 requirements 文件（利用 Docker 缓存层）
COPY src/requirements.txt /app/src/requirements.txt
COPY backend/requirements.txt /app/backend/requirements.txt

# 安装 src 依赖
RUN pip install --no-cache-dir -r /app/src/requirements.txt
# 安装 backend 依赖
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# ---------- Download spaCy Model ----------
RUN python -m spacy download en_core_web_sm

# ---------- Copy Source Code ----------
# 复制核心业务逻辑
COPY src/ /app/src/
# 复制 FastAPI 应用
COPY backend/ /app/backend/

# ---------- Copy Data Files ----------
# 大纲文件和语料库（如果存在）
COPY data/ /app/data/

# ---------- Non-root User (Security) ----------
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# ---------- Expose Port ----------
EXPOSE 8000

# ---------- Health Check ----------
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# ---------- Entry Point ----------
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
