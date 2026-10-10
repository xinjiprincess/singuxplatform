#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# 一键 Docker 镜像构建脚本
# 用法:
#   ./docker-build.sh                    # 使用默认镜像名和 latest 标签
#   ./docker-build.sh -t v1.1.10         # 指定镜像标签
#   ./docker-build.sh -n my-registry/frontend -t v1.1.10
#   ./docker-build.sh --china-mirror     # 使用华为云/国内镜像源
# ============================================================

# 默认值
IMAGE_NAME="singular-origo-frontend"
TAG="latest"
FULL_TAG=""
USE_CHINA_MIRROR=false
NODE_IMAGE="node:22.10.0"
NGINX_IMAGE="nginx:alpine"
NPM_REGISTRY="https://registry.npmmirror.com"
PUSH_AFTER_BUILD=false

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印帮助信息
show_help() {
  cat <<EOF
用法: $0 [选项]

选项:
  -n, --name IMAGE_NAME      镜像名称 (默认: singular-origo-frontend)
  -t, --tag TAG              镜像标签 (默认: latest, 也可传版本号如 v1.1.10)
  -r, --registry REGISTRY    镜像仓库前缀 (如 docker.io/username)
  --china-mirror             使用国内镜像源加速构建
  --push                     构建完成后推送到镜像仓库
  -h, --help                 显示此帮助信息

示例:
  $0                                    # 构建 singular-origo-frontend:latest
  $0 -t v1.1.10                         # 构建 singular-origo-frontend:v1.1.10
  $0 -n my-repo/frontend -t v1.1.10     # 构建 my-repo/frontend:v1.1.10
  $0 --china-mirror -t v1.1.10          # 使用国内镜像源构建
  $0 -r registry.cn-hangzhou.aliyuncs.com/myname -t v1.1.10 --push
EOF
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--name)
      IMAGE_NAME="$2"
      shift 2
      ;;
    -t|--tag)
      TAG="$2"
      shift 2
      ;;
    -r|--registry)
      REGISTRY_PREFIX="$2"
      shift 2
      ;;
    --china-mirror)
      USE_CHINA_MIRROR=true
      shift
      ;;
    --push)
      PUSH_AFTER_BUILD=true
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo -e "${RED}未知参数: $1${NC}"
      show_help
      exit 1
      ;;
  esac
done

# 组合完整镜像名
if [[ -n "${REGISTRY_PREFIX:-}" ]]; then
  FULL_TAG="${REGISTRY_PREFIX}/${IMAGE_NAME}:${TAG}"
else
  FULL_TAG="${IMAGE_NAME}:${TAG}"
fi

# 国内镜像加速
if [[ "$USE_CHINA_MIRROR" == true ]]; then
  NODE_IMAGE="swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:22.10.0"
  NGINX_IMAGE="swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nginx:alpine"
  NPM_REGISTRY="https://registry.npmmirror.com"
  echo -e "${BLUE}已启用国内镜像加速${NC}"
fi

# 检查 Docker 环境
echo -e "${BLUE}正在检查 Docker 环境...${NC}"
if ! command -v docker >>/dev/null 2>&1; then
  echo -e "${RED}错误: Docker 未安装或未加入 PATH${NC}"
  exit 1
fi

if ! docker info >>/dev/null 2>&1; then
  echo -e "${RED}错误: Docker 守护进程未运行${NC}"
  exit 1
fi

echo -e "${GREEN}Docker 环境正常${NC}"

# 显示构建信息
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  镜像名称: ${FULL_TAG}${NC}"
echo -e "${BLUE}  Node 镜像: ${NODE_IMAGE}${NC}"
echo -e "${BLUE}  Nginx 镜像: ${NGINX_IMAGE}${NC}"
echo -e "${BLUE}  NPM 镜像源: ${NPM_REGISTRY}${NC}"
echo -e "${BLUE}========================================${NC}"

# 构建镜像
echo -e "${YELLOW}开始构建 Docker 镜像...${NC}"
docker build \
  --build-arg NODE_IMAGE="${NODE_IMAGE}" \
  --build-arg NGINX_IMAGE="${NGINX_IMAGE}" \
  --build-arg NPM_REGISTRY="${NPM_REGISTRY}" \
  -t "${FULL_TAG}" \
  -f Dockerfile \
  .

BUILD_STATUS=$?

if [[ $BUILD_STATUS -ne 0 ]]; then
  echo -e "${RED}========================================${NC}"
  echo -e "${RED}  Docker 镜像构建失败${NC}"
  echo -e "${RED}========================================${NC}"
  exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Docker 镜像构建成功${NC}"
echo -e "${GREEN}  镜像: ${FULL_TAG}${NC}"
echo -e "${GREEN}========================================${NC}"

# 可选：推送镜像
if [[ "$PUSH_AFTER_BUILD" == true ]]; then
  echo -e "${YELLOW}正在推送镜像到仓库...${NC}"
  docker push "${FULL_TAG}"
  echo -e "${GREEN}镜像推送完成: ${FULL_TAG}${NC}"
fi

# 显示运行命令示例
echo ""
echo -e "${BLUE}运行示例:${NC}"
echo -e "  ${YELLOW}docker run -d -p 80:80 --name singular-origo-frontend ${FULL_TAG}${NC}"
echo ""
echo -e "${BLUE}查看镜像:${NC}"
echo -e "  ${YELLOW}docker images | grep ${IMAGE_NAME}${NC}"
