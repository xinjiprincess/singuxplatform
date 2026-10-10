# Singu X 平台服务器部署包

包版本：`1.1.10-20260924-r1`，平台：Linux x86_64 / amd64。
前端基线为 `1.1.10`，后端基线为 `0.0.1-SNAPSHOT`，包含 Singu X 中文文案和管理员用户名登录修复。

## 包内内容

- `images.tar`：前端、后端、MySQL、Redis、etcd、MinIO、Milvus、Elasticsearch 共八个运行镜像，可离线导入。
- `compose.json`：服务器专用 Docker Compose 配置，无源码构建步骤或 Windows 路径，只对外发布网站端口。
- `mysql/`：全新数据库初始化 SQL；仅在 MySQL 数据卷为空时执行。
- `migrations/`：后端语言初始化完成后补充登录页账户提示。
- `.env.example`、`deploy.sh`：环境配置模板和一键部署脚本。
- `images.json`、`SHA256SUMS`、`VERSION_CHANGES.md`、`licenses/`：镜像清单、校验文件、改动记录和前后端许可文件。

这是全新安装包，不含本机业务数据库、上传文件、模型 API Key 或用户数据。全新安装会从打包时的后端初始化 SQL 创建管理员与默认数据。

## 部署

服务器需已安装并启动 Docker，以及支持 `up --wait` 的 Docker Compose v2。建议为完整服务栈预留至少 4 核、16 GB 内存和 30 GB 可用磁盘，实际需求随数据量变化。

上传 `.tar.gz` 压缩包及同名 `.sha256` 文件到服务器，在同一目录执行：

```sh
sha256sum -c singu-x-1.1.10-20260924-r1-linux-amd64.tar.gz.sha256
tar -xzf singu-x-1.1.10-20260924-r1-linux-amd64.tar.gz
cd singu-x-1.1.10-20260924-r1-linux-amd64
sh deploy.sh
```

脚本会校验文件、为数据库等服务生成随机密码、导入镜像，并等待服务启动。访问 `http://服务器IP:8080`，选择“密码登录”，使用用户名 `admin`、初始密码 `123456`。登录后修改初始密码。

服务器防火墙或云安全组需允许网站端口。MySQL、Redis、Elasticsearch、Milvus、MinIO 等服务仅在 Docker 网络内可用。

## 配置与维护

首次运行会生成 `.env`，之后重跑脚本会保留该文件。网站端口默认是 `8080`；修改 `.env` 中的 `FRONTEND_PORT` 后运行以下启动命令应用配置。切勿在保留数据库卷时随意更换数据库密码。

```sh
# 启动或应用配置
docker compose --env-file .env -f compose.json up -d --no-build --pull never
# 查看状态
docker compose --env-file .env -f compose.json ps
# 查看应用日志
docker compose --env-file .env -f compose.json logs -f frontend backend
# 停止服务并保留数据卷
docker compose --env-file .env -f compose.json down
```

部署项目名默认 `singux`，持久化数据由相应 Docker 命名卷保存；备份时同时保存 `.env`、数据库及上传文件卷。不要使用 `down -v`，该参数会删除数据卷。

## 功能范围

包内提供网站、后端和基础数据服务。模型调用需在系统管理中配置实际模型与密钥；AppDev、代码执行、构建、日志及智能体运行服务需另行部署，并在 `.env` 中填写对应地址。`host.docker.internal` 默认指向当前服务器宿主机。

当前 `DORIS_*` 配置沿用本地环境指向 MySQL 兼容库，未包含独立 Doris 服务，也未验证完整分析功能。默认智能体的部分图片使用外部 CDN，完全断网环境可能无法显示这些图片。离线镜像导入不代表所有业务功能都可断网运行。

镜像基于本地已通过登录验证的版本打包；实际服务器网络、资源、域名、HTTPS、外部服务需在部署后核对。平台展示名称、登录页中文文案和默认页脚配置来自后端默认值。
