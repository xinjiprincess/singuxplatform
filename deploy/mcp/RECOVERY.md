# 20261009 单租户知识库与 MCP 联合修复候选包

## 2026-10-10 旧平台缓存与历史状态修复

- 实机发现 `/home/mcp` 256 MB tmpfs 已满、`/tmp` 256 MB 使用 97%，npm 安装直接返回 ENOSPC；仅容器 health 正常不能证明新 MCP 能部署。
- `fix-production-cache.py` 已备份旧缓存和配置，将两处目录改为仅 MCP 使用的 Docker 命名卷，UID/GID 10001 可写。代理仍非 root、只读根文件系统、无 Docker socket、无宿主目录挂载、保留 1536 MB 内存限制。只重启代理，后端容器未变。
- 专用缓存卷无自动容量配额，后续需监控 Docker 数据盘及 npm/uv 缓存增长，不能把卷误称为不限资源的沙箱。旧缓存备份 `/data/singux-mcp-cache-repair-20261010`；不自动删除缓存或用户文件。
- `compose.cache.json` 是供后续部署审查的缓存配置参考，不是可直接盲目叠加的生产更新：Compose 的 tmpfs 列表可能合并，必须在解析后的最终配置中明确移除原 `/home/mcp`、`/tmp` tmpfs，先初始化外部卷及所有权。已上线脚本直接修改原 MCP 叠加文件避免列表合并歧义。
- `repair-stale-production.py` 仅修正超过一小时且没有 CONTINUE/EXECUTING 部署任务的历史 Deploying 状态，备份后改为 DeployFailed，允许所有者显式重试；不标假成功，不更改配置、有效任务或已部署服务。
- Excel 服务 ID 16 的 Hub CLI 实测报 `e.filter is not a function`；直接包 0.12.0 经隔离启动和 6 个工具发现后，已替换为直接 npx 命令。保留失败状态，所有者在界面重新部署后才完成业务发布；未运行任何 Excel 文件读写工具。原配置 `excel-16.before.json` 在服务器私有修复目录，不含到公开文档中。

## 包内内容

- 后端 `singux/backend:1.1.10-20261009-service-recovery-mcp-r1`：保留知识库问答模型选择和全文索引修复，加入 MCP 代理异常/创建者缺失时的失败状态回写。
- MCP 代理 `singux/mcp-proxy:0.2.8-20261009-recovery-r1`：已有 Node/npm/uv 运行环境、非 root、只读根文件系统；内置锁定依赖的文件工具供隔离测试使用，不自动添加到企业或用户的服务列表。
- `compose.mcp.json`：叠加到原部署 Compose，后端 `MCP_PROXY_URL=http://mcp-proxy:8080`；代理只有 Docker 内网服务，没有宿主端口、Docker socket 或宿主文件挂载。
- 镜像归档、镜像摘要、来源记录、校验清单。没有数据库、账号名单、模型密钥或 `.env`，没有切换多租户、比赛入口或前端。

## 导入与配置检查

本地验证：代理健康检查、通过代理的 MCP 握手、14 个工具列表和真实只读工具调用通过；无效命令返回明确 Error。后端代理异常、创建者缺失、Pending 继续轮询和重试上限失败回写四项测试通过。该结果不代表服务器上每个第三方 MCP 包均已部署成功。

先验证外部归档校验，再解压并运行：

```sh
sha256sum -c SHA256SUMS
docker load -i images.tar
```

以上只加载镜像，不替换运行服务。将 `compose.mcp.json` 复制到原部署目录，不覆盖原 `compose.json` 或 `.env`。使用原项目名和原环境文件检查合并配置；`config` 可能包含密钥，不要把完整输出上传或粘贴到聊天：

```sh
cd /home/singu-x-1.1.10-20260924-r1-linux-amd64
docker compose -p singux --env-file .env -f compose.json -f compose.mcp.json config --quiet
```

如果原后端配置使用自定义网络，必须确保后端和代理共用一个受控网络；当前叠加文件按默认 Compose 网络设计。保留该叠加文件，以后更新同样带两个 `-f`，避免后端回到旧地址。

## 本次专用更新器

2026-10-09 已在 `43.136.175.19` 完成授权部署，结果 `DEPLOY_OK`。最终备份目录 `/data/singux-backups/mcp-20261008T172207Z`，本地验收记录 `outputs/mcp-production-deployment-20261009.json`。MCP 握手、14 个工具列表和真实只读调用通过；公网 HTTPS 登录页及公开配置通过。6 张业务表数量和原 8 服务挂载一致，前端/后端/MySQL/MCP healthy。此记录不代表全部用户服务或所有业务验收通过。

本次生产部署使用 `update-production.py`，不是旧知识库更新器。默认执行只读预检；`--apply` 才备份并切换。仅适用于本次已核验的原后端 JAR、原部署目录、8 个服务和 Linux amd64 环境，不可直接重复运行或用于其他基线。

更新器备份 SQL、所有挂载卷和配置，校验备份可读性、业务表数量、数据挂载路径以及 MCP 真实工具调用。失败时回退镜像和配置，不用旧数据覆盖当前数据库。该检查不能代替完整恢复演练或用户实际业务验收。

生产历史 Pending 安装同时启动，原 128 进程上限触发 `Cannot fork` 后已回退。本次专用更新器调整代理为 512 进程、1536 MB 内存及 2 个 Tokio 工作线程，CPU 仍限 1 核，不移除非 root、只读、权限和网络限制。此资源覆盖在专用更新器内实施，已上传归档本身及校验值不改变。

成功后保留原 `compose.json` 和 `.env`，增加 `compose.mcp.json`。后续查看和启动均带两个配置文件：

```sh
cd /home/singu-x-1.1.10-20260924-r1-linux-amd64
docker compose -p singux --env-file .env -f compose.json -f compose.mcp.json ps
docker compose -p singux --env-file .env -f compose.json -f compose.mcp.json up -d --no-build --pull never
```

只使用原 `compose.json` 启动可能切回旧后端，且不会管理新增 MCP 服务。不要执行 `down -v` 或删除数据卷。备份目录含敏感数据库及环境配置，应限制权限并另行离机保存。

## 候选包限制

此包仍为 `productionApproved=false`。生产切换前，备份数据库、上传文件、数据卷及 Compose/环境配置，记录旧运行镜像摘要，并在复制环境验证启动和业务。不要使用上一次固定旧基线的 `update-knowledge.py` 安装本包，不执行 `down -v`、`volume prune` 或数据库清空。

备份及发布审查通过后，可在原项目内按叠加配置只更新 `mcp-proxy` 和 `backend`；不需要重建 MySQL、MinIO、Milvus、Elasticsearch 或前端。旧数据不会被包主动覆盖，但备份和恢复验证仍不可省略。失败时切回记录的旧后端镜像和旧配置，不自动用旧数据库覆盖新增数据。

现有卡在“部署中”的服务需要在平台中逐个重新部署，不能直接修改数据库为成功。上游 MCP 包、模型授权及环境变量缺失仍会使各自服务失败；不保证任意 NPX 包均可用。代理执行用户配置的命令，当前共享代理不是完整多租户进程隔离方案，企业开放接入前需加强命令策略与执行节点隔离。

文件工具的锁定依赖仅用于测试夹具，不对其他用户工具强行降级。学校问答接口授权 401、图片代理 403 和生产智能体电脑接入不在本次 MCP 验收范围内。
# MCP failure logs (2026-10-10)

The single-tenant logging patch is built from the verified production baseline,
not the local tenant-enabled application. It updates only MCP application/UI
modules and does not migrate SQL or replace data volumes.

- Generate: `python deploy/mcp/package-logging-patch.py`.
- Regression: `deploy/tests/test-mcp-logging.ps1 -ProductionBaseline`.
- Production updater: `deploy/mcp/update-production-logging.py`, with strict
  baseline digest, original Compose labels, preserved environment/mounts and
  automatic image/config rollback on failed startup checks.
- Verify through normal owner APIs using `verify-production-logging.py`:
  temporary failed deployment and unsuccessful component invocation, followed
  by `/api/requestLogs/list`. Credentials arrive over stdin, never as files.
- Logs use `targetType=Mcp`, `targetId=<service id>`, `resultCode=0001`.
  Deployment records additionally use `from=McpDeploy` and a `mcp:<id>:...`
  request ID. Existing records are not retroactively reconstructed.
- Records enter the existing Redis queue and Elasticsearch indexing job;
  visibility is asynchronous. Logging infrastructure failure still emits a
  sanitized backend error, but this patch is not a guaranteed-delivery queue
  redesign. Proxy package stderr is not automatically copied into platform logs.
