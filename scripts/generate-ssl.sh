#!/bin/bash
# ============================================
# VocabWeaver SSL Certificate Generator
# ============================================
# 生成自签名证书用于开发/测试环境
# 生产环境请使用 Let's Encrypt 或购买证书
# ============================================

set -e

SSL_DIR="$(dirname "$0")/../ssl"
mkdir -p "$SSL_DIR"

echo "生成 SSL 证书..."

# 生成私钥
openssl genrsa -out "$SSL_DIR/key.pem" 2048

# 生成自签名证书（有效期 365 天）
openssl req -new -x509 -key "$SSL_DIR/key.pem" -out "$SSL_DIR/cert.pem" -days 365 \
    -subj "/C=CN/ST=Beijing/L=Beijing/O=VocabWeaver/OU=IT/CN=localhost"

# 设置权限
chmod 600 "$SSL_DIR/key.pem"
chmod 644 "$SSL_DIR/cert.pem"

echo "✓ SSL 证书已生成:"
echo "  - $SSL_DIR/cert.pem"
echo "  - $SSL_DIR/key.pem"
echo ""
echo "⚠ 警告: 这是自签名证书，仅用于开发/测试环境"
echo "生产环境请使用 Let's Encrypt 或购买正式证书"
