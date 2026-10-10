# Caddy HTTPS 接入

## 本机测试

`compose.local.yml` 使用 C 盘 `dist`，连接既有独立测试网络 `singux-local_default` 和后端 `singux-local-backend-1`。执行 `docker compose -f deploy/caddy/compose.local.yml up -d`，入口为 `http://127.0.0.1:18090`。必须先启动测试后端和依赖；不要与旧 18090 预览容器同时运行。

本机明确禁用自动 HTTPS，不申请证书、不改 DNS；不代表公共域名或客户自定义域名的 HTTPS 已验收。

本机后端仍使用 Java 运行时镜像 `singular-origo-backend:local`，只读挂载 `D:/singuxplatform/nuwax-backend/app-platform-bootstrap/app-platform-web-bootstrap/target/app-platform-web-bootstrap-0.0.1-SNAPSHOT.jar`。这是本地挂载测试，不是新的离线发布镜像。后端打包后需重启 `singux-local-backend-1`。

已有测试容器停止后，可在 C 盘前端根目录恢复（仅适用于本机已有环境，不是全新安装）：

```powershell
docker start singux-local-mysql-1 singux-local-redis-1 singux-local-etcd-1 singux-local-minio-1 singux-local-milvus-1 singux-local-elasticsearch-1
docker start singux-local-backend-1
docker compose -f deploy/caddy/compose.local.yml up -d
docker ps --filter name=singux-local
```

数据库和上传卷继续使用 `singux-local_*`，不使用旧 `singular-origo-*` 数据。成员和租户策略开关保持关闭，未通过全链路隔离验收前不得用于多企业生产服务。

## 公共域名部署

当前配置只开放已确定的公共入口 `www.ciyuancenter.cc`，未开放任意客户域名或通配的按需签证，避免未经验证的域名触发签证。

运行 Caddy 2 时必须与前端服务加入同一个 Docker 网络，挂载 Caddyfile 到 `/etc/caddy/Caddyfile`，持久化 `/data` 和 `/config`，只向公网发布 Caddy 的 80/443 端口。后端及数据库不得发布公网端口。

API 由 Caddy 直接代理后端，避免内层 Nginx 将 HTTPS 协议头覆盖为 HTTP。仅在后端端口无法被外部绕过网关访问时设置 `SERVER_FORWARD_HEADERS_STRATEGY=framework`；不得对开放公网的后端无条件信任 Forwarded 头。

设置 `ACME_EMAIL` 为运维邮箱。默认 `ACME_CA` 为 Let's Encrypt 测试环境，不产生浏览器可信证书；DNS A/AAAA 指向服务器且测试签证成功后，显式设置 `https://acme-v02.api.letsencrypt.org/directory`。

此文件没有修改服务器或 DNS，也不代表证书签发/续期已验收。客户自定义域名仍须完成付费权益检查、唯一域名注册、TXT 验证、解析检查、Caddy 签证授权接口以及域名与租户会话匹配，不能直接添加 `https://` 通配站点绕过这些检查。

部署覆盖文件（要求 Docker Compose 2.24.4+）：

```sh
docker compose --env-file .env.compose -f docker-compose.yml -f deploy/caddy/compose.yml config --quiet
# 仅在已核对服务器域名、备份和端口后执行：
docker compose --env-file .env.compose -f docker-compose.yml -f deploy/caddy/compose.yml up -d
```

覆盖文件关闭 MySQL/Redis/MinIO/Milvus/Elasticsearch 的宿主机端口，前端原 HTTP 端口仅绑定回环地址；Caddy 持久化证书。不要在本机测试时直接占用已有服务的 80/443。生产发布前应固定通过验证的 Caddy 镜像版本/摘要。

参考：[Caddy Automatic HTTPS](https://caddyserver.com/docs/automatic-https)、[On-demand TLS](https://caddyserver.com/docs/caddyfile/options#on-demand-tls)。
