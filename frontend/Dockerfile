# ============================================
# VocabWeaver Frontend Dockerfile
# ============================================
# 多阶段构建：
# Stage 1: Node.js 构建静态文件
# Stage 2: Nginx 托管静态文件
# ============================================

# ============================================
# Stage 1: Build (Node.js)
# ============================================
FROM node:20-alpine AS builder

WORKDIR /app

# ---------- Install Dependencies ----------
# 先复制 package 文件（利用缓存层）
COPY frontend/package.json frontend/package-lock.json* ./

# 安装依赖
RUN npm ci --legacy-peer-deps || npm install

# ---------- Copy Source ----------
COPY frontend/ .

# ---------- Environment Variables ----------
# 构建时注入后端 API 地址（可通过 build-arg 覆盖）
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# ---------- Build ----------
RUN npm run build

# ============================================
# Stage 2: Production (Nginx)
# ============================================
FROM nginx:alpine AS production

# ---------- Remove Default Config ----------
RUN rm /etc/nginx/conf.d/default.conf

# ---------- Custom Nginx Config ----------
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# ---------- Copy Built Assets ----------
COPY --from=builder /app/dist /usr/share/nginx/html

# ---------- Non-root User (Security) ----------
RUN chown -R nginx:nginx /usr/share/nginx/html \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/run/nginx.pid

USER nginx

# ---------- Expose Port ----------
EXPOSE 80

# ---------- Health Check ----------
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
