# 本地 Docker 构建

日期：2026-09-29。本轮只构建本机镜像，不推送仓库、不执行在线发布、不更新生产服务器。

## 入口

在前端仓库执行：

```powershell
.\deploy\build-local.ps1
# 只构建指定组件
.\deploy\build-local.ps1 -Components frontend,file-server
```

前端使用脚本所在仓库的根目录；后端和配套服务默认在 `D:\singuxplatform`。
脚本遇到任何构建错误立即停止，不替换运行容器、不删除数据卷。

| 组件 | 本地镜像标签 |
| --- | --- |
| 前端 | `singux/frontend:1.1.10-20260929-local` |
| 后端 | `singux/backend:1.1.10-20260929-r4` |
| MCP | `singux/mcp-proxy:0.2.8-local` |
| 文件服务 | `singux/file-server:1.5.4-20260929-local` |
| RCoder 调度与网页执行器 | `singux/rcoder:20260929-local` |

以上五个镜像本轮均构建成功，并核对为 Linux amd64。

本机构建复用了已有 `master-rcoder-base:latest` 与 MCP 基础镜像。不能只凭这份脚本认定其他机器能够从零复现；正式发布前仍需将所有基础层和上游工具版本固定到可获取的制品。
RCoder 的官方镜像还安装了多个使用浮动版本的 ACP 工具，本轮仅作本地构建，不视为经过发布审计的生产镜像。

## 网络与构建修正

- npm/pnpm 使用国内镜像下载，文件服务遵循仓库 pnpm lockfile。
- RCoder 编译产物先保存为 `20260929-build`，再构建本地运行层，规范化两个启动脚本的 CRLF 换行并进行 Bash 语法检查；默认命令改为 RCoder，不再沿用 Node 基础镜像的交互命令。
- 前端构建排除 `.env.compose`、历史镜像归档、JAR 和其他无关输出，不更改实际部署环境文件。
- RCoder Dockerfile 新增 `CARGO_USE_MIRROR` 和 `CARGO_BUILD_JOBS` 参数以及依赖缓存。
- 本机 BuildKit 默认网络内的 Cargo 域名解析失败；普通容器的 Cargo 请求成功。构建脚本仅对 Rust 构建使用 `--network host`，没有修改 Docker 全局配置；可通过 `-RustBuildNetwork default` 覆盖。
- Cargo 默认两个并行编译任务；本地脚本切换到官方依赖源，因为本次镜像源解析失败。
- 仅切换 host 构建网络仍无法解析包下载域名。脚本默认从 Windows DNS 查询两个 crates.io 域名的当前 IPv4，使用 `--add-host` 传入本次构建，保留 HTTPS 域名与证书校验，不修改系统 hosts，也不硬编码长期 IP。网络正常时可用 `-ResolveCargoHosts:$false` 关闭。

## 已验证入口

- 最新菜单移除版本：`singux/frontend:1.1.10-20260929-menu`，容器 `singux-frontend-menu-test`，入口 `http://127.0.0.1:18092/login`。健康与登录页面 HTTP 200、租户配置 `0000`。使用原本地 r3 后端；比赛专用入口尚未实现。18091 存在其他项目同端口声明，因此新测试使用 18092。

- 新前端测试容器 `singux-frontend-build-test`：`http://127.0.0.1:18091/login`。
- 登录页和前端健康接口 HTTP 200；经该入口访问后端公开租户配置返回成功。
- 此前端连接原本地后端容器，尚未把已构建 r4 自动切换进去；原 18090 入口未改动。
- 文件服务新镜像已在无网络、无宿主挂载的临时容器启动并通过 HTTP 健康检查；测试容器随后清理，原文件服务保留。
- MCP 独立测试及工具调用结果见 `runtime-recovery-and-updates.md`。
- RCoder 最终镜像在无网络、无宿主挂载的临时容器中通过 `rcoder --version`（0.1.3）、`agent_runner --help` 和 `file-server --version`（0.1.1）；两个启动脚本通过 Bash 语法检查。未挂载 Docker socket，未启动实际沙箱或替换原服务。

HTTP 健康与镜像构建不等于沙箱、网页生成、预览或生产 MCP 全链路验收。构建失败必须如实记录，不能使用旧 `latest` 镜像冒充本次成果。
# 2026-09-29 比赛入口补充

新增本地预览端口 `18093`，比赛入口 `/zhichuangbei/login`，官网 `/login`，平台管理员入口 `/platform/portals`。本地比赛租户 ID 为 4，数据库 ID 不应直接照搬到生产。

构建命令（前端工作目录 `C:\Users\zhang\nuwax`）：

```powershell
docker build --build-arg NODE_IMAGE=master-rcoder-base:latest -t singux/frontend:1.1.10-20260929-portal .
docker build -f deploy/backend-release.Dockerfile -t singux/backend:1.1.10-20260929-portal D:/singuxplatform/nuwax-backend
./deploy/run-local-portal.ps1
./deploy/test-local-portal.ps1
```

本机 Node 基础镜像用于复用已经存在的依赖环境；其他环境可用 Dockerfile 默认 Node 镜像。先运行后端迁移 `sql/migrations/20260929-portals.sql`；本地测试种子为前端 `deploy/migrations/20260929-portal-local-seed.sql`。种子仅供已有 admin/tenant 1 的本地开发环境，不是生产通用迁移。另须初始化目标租户权限模板，见比赛调试文档。

启动脚本保留原本地后端容器备份，健康失败则恢复；复用原数据卷，开启 `PLATFORM_PORTALS_ENABLED=true`，还要求原有 membership/policy 开关启用。不会修改服务器。成功后旧容器保持停止，不删除其数据或数据库。新前端无数据卷，可安全重建；后端升级不等于数据库回滚，禁止删除现有卷。

以下保留早期构建记录，旧端口、旧镜像及未完成范围不代表本轮最终状态。
