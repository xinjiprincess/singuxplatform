# ==========================================
# 阶段一：构建前端应用
# ==========================================
ARG NODE_IMAGE=node:22.10.0
ARG NGINX_IMAGE=nginx:alpine
FROM ${NODE_IMAGE} AS builder

WORKDIR /app

# 安装 pnpm（与 package.json 中 packageManager 保持一致）
RUN npm install -g pnpm@10.27.0

# 先复制依赖相关文件，利用 Docker 缓存层
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
COPY scripts ./scripts

# 安装依赖（使用国内镜像加速，构建时可传入 registry 参数覆盖）
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN pnpm fetch --registry=${NPM_REGISTRY}

# 复制项目源码（.dockerignore 已排除不需要的文件）
COPY . .

# 在源码已复制后安装依赖，避免 postinstall 阶段的 max setup 缺少项目文件
RUN pnpm install --registry=${NPM_REGISTRY} --frozen-lockfile --offline

# 复制新品牌 Logo 到构建目录（如存在 hj_icon）
RUN mkdir -p public/logo && \
    if [ -d "hj_icon" ]; then \
      cp hj_icon/微信图片_20260531155429_4108_1207.png public/logo/logo-light.png 2>/dev/null || true; \
      cp hj_icon/微信图片_20260531155428_4107_1207.png public/logo/logo-dark.png 2>/dev/null || true; \
      cp hj_icon/微信图片_20260531155430_4109_1207.png public/logo/logo-dark-compact.png 2>/dev/null || true; \
      cp hj_icon/微信图片_20260531155433_4112_1207.png public/logo/company-name.png 2>/dev/null || true; \
    fi

# 构建生产包
ENV NODE_ENV=production
ENV BABEL_CACHE=none
RUN pnpm run build:prod

# ==========================================
# 阶段二：Nginx 静态服务器
# ==========================================
FROM ${NGINX_IMAGE}

WORKDIR /usr/share/nginx/html

# 复制 Nginx 配置模板，交给官方 nginx entrypoint 在容器启动时做 envsubst
COPY ./k8s/default.conf.template /etc/nginx/templates/default.conf.template

# 从 builder 阶段复制构建产物
COPY --from=builder /app/dist .

ENV SERVER_NAME=_
ENV URI_NAME='$uri'
ENV API_UPSTREAM=http://backend:8081
ENV MODEL_PROXY_UPSTREAM=http://backend:18086

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/__frontend_health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
