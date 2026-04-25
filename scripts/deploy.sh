#!/bin/bash
# ============================================
# VocabWeaver Deployment Script
# ============================================

set -e

echo "========================================"
echo "  VocabWeaver 部署脚本"
echo "========================================"

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠ .env 文件不存在，从模板创建..."
    cp .env.example .env
    echo "✓ 已创建 .env 文件，请编辑并填入 API_KEY"
    exit 1
fi

# 选择环境
ENV=${1:-dev}
echo "环境: $ENV"

if [ "$ENV" = "prod" ]; then
    # 检查 SSL 证书
    if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
        echo "⚠ SSL 证书不存在，生成自签名证书..."
        bash scripts/generate-ssl.sh
    fi

    echo "构建生产镜像..."
    docker-compose -f docker-compose.prod.yml build --no-cache

    echo "启动生产服务..."
    docker-compose -f docker-compose.prod.yml up -d

    echo ""
    echo "✓ 生产环境部署完成"
    echo "  - HTTPS: https://localhost"
    echo "  - API: https://localhost/api"
    echo "  - Docs: https://localhost/docs"
else
    echo "构建开发镜像..."
    docker-compose build --no-cache

    echo "启动开发服务..."
    docker-compose up -d

    echo ""
    echo "✓ 开发环境部署完成"
    echo "  - HTTP: http://localhost"
    echo "  - API: http://localhost:8000/api"
    echo "  - Docs: http://localhost:8000/docs"
fi

echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
