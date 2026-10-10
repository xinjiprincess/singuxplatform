# MCP、沙箱、网页应用与在线更新

日期：2026-09-29。本文区分本地验证与生产发布，不代表全部修复完成。

## 2026-10-10 文档静态更新

- 后续用户授权旧官网同步：`43.136.175.19` 已上线同一文档包，正式入口 `https://www.ciyuancenter.cc/docs/`，菜单使用同源 iframe。旧官网备份 `/data/singux-docs-20261010/release`；沿用原四份 Compose，只更新前端镜像与菜单。下述“旧服务器未改变”指首次新服务器部署阶段，已被本次明确授权更新。
- 官网宿主 Nginx 原先将文档转发至下载服务，响应 DENY 阻止 iframe。已仅调整 `/docs` 和 `/docs/` 路由到前端 8080，并限定同源嵌入；下载站和管理入口不变。回滚网关可使用上述备份中的 `gateway.before.conf` 还原片段，再执行 `nginx -t` 与 reload；不要直接执行整库回滚。
- 文档资源随前端镜像内置，入口 `/docs/`，无需数据库服务或独立 Python 服务；阅读不需要登录，PDF 为 `/docs/download/manual.pdf`。
- 本地源代码新增书本菜单图标，生产构建后使用 `deploy/frontend-docs.Dockerfile` 构建本地预览镜像。不要将本地租户版整体镜像直接覆盖线上单租户版。
- 新迁移服务器已用 `deploy/services/deploy-migration-docs.py` 完成原镜像上的文档窄更新，既有菜单改为同源 iframe。脚本保存原 Compose、Nginx 模板和菜单配置；失败自动尝试还原。首次部署脚本拒绝覆盖已有发布目录，不要反复执行。
- 新服务器已实测登录后菜单点击及桌面/手机文档功能。本机 SSH 通道 `http://127.0.0.1:18109/docs/` 可预览；旧服务器与 DNS 未改变，公网可达性问题仍独立待处理。

## 本轮状态

2026-10-10 迁移目标补验：`verify-migration-mcp.py` 在目标运行隔离文件工具，后端到代理部署检查、SSE 握手、工具列表和只读调用通过。结果文件 `mcp-verification.json`；不更改用户服务配置，也不代表用户所有外部 MCP 服务已通过。模型出站隔离、公网和增量限制保持不变。

| 范围 | 已验证 | 尚未完成 |
| --- | --- | --- |
| MCP | 独立容器健康；官方文件工具通过代理返回 14 个工具并成功执行只读调用；后端部署失败回写测试通过 | 生产部署、现存 MCP 配置逐个重试、租户级运行时隔离 |
| 沙箱 | 官方 RCoder 源码已下载；确认调度服务与动态 agent_runner 容器关系 | 匹配版本镜像构建、权限边界、真实创建/回收验收 |
| 网页应用 | 后端调用 `/chat` 和 `/agent/progress/{session_id}`，RCoder 源码存在对应路由；文件服务创建接口存在 | 创建、编辑、生成、预览、发布及鉴权的完整联调 |
| 在线更新 | 新增 HTTPS 清单下载入口；现有更新流程 10 项回归通过 | 镜像仓库、可信发布清单分发、生产演练、管理端按钮、辅助服务更新 |

## 目录和版本

- 前端、部署工具和本文：`C:\Users\zhang\nuwax`。
- 后端：`D:\singuxplatform\nuwax-backend`。
- 配套服务：`D:\singuxplatform\mcp-proxy`、`rcoder`、`nuwax-file-server`。
- 下载源码的 commit、MCP 官方二进制校验和见 `deploy/mcp/sources.json`。
- RCoder 当前版本内置 Rust 文件服务。不能在未核对工作目录和接口前，与旧 Node 文件服务同时接管项目。
- 本机已有旧 RCoder 镜像，但不能据此断言它与本次下载源码一致。

## MCP 本地验证

配置：`deploy/mcp/compose.test.yml`，镜像 `singux/mcp-proxy:0.2.8-local`，仅绑定 `127.0.0.1:18020`。
容器无 Docker socket、无宿主目录挂载，非 root、只读根文件系统、禁止提权，设置进程/内存/CPU 限额。
这是单独的兼容性测试环境，不是多租户安全隔离方案，也未接入业务后端。

构建需从官方 v0.2.8 发布页下载 Linux amd64 归档到 `deploy/mcp/mcp-v0.2.8.tar.xz`。
Dockerfile 内校验归档 SHA256。运行基础层暂复用本机已有镜像，发布前必须锁定仓库 digest 并审计其来源。

```powershell
docker compose -f deploy/mcp/compose.test.yml build
docker compose -f deploy/mcp/compose.test.yml up -d --wait
```

测试发现的两个问题：

1. 上游启动时自动预热 Python/JS 依赖，会占用临时空间。测试配置禁用 Python 自动下载，并分离 uv/npm 缓存；脚本执行服务尚未验收。
2. `server-filesystem@2025.8.21` 的浮动依赖解析为新版 SDK/Zod 时产生无效工具 schema，直接 stdio 连接也复现。测试缓存中锁定 SDK 1.17.0、Zod 3.25.76、zod-to-json-schema 3.24.6 后通过。生产工具必须逐个锁定并验证依赖，不可全局强制降级其他工具。

测试使用 MCP ID `singux-local-smoke`，通过 `/mcp/sse/check_status` 提交文件工具配置，仅授权容器 `/tmp`。缓存目录需要允许执行 npm 包，仍保留 nosuid/nodev。
`deploy/mcp/smoke-call.mjs` 验证握手、工具列表和 `list_allowed_directories` 调用，可通过标准输入执行；`--direct` 用于与代理链路比较。
临时缓存会随容器重新创建丢失，因此上述依赖修正不是可复现生产镜像的完成证明。

## 沙箱与网页应用接入要求

1. 将调度器、执行容器、文件存储和预览网关的职责分开。只向公网暴露经过鉴权的业务入口，不暴露调度 API、终端或 Docker API。
2. RCoder 官方开发 Compose 挂载宿主 Docker socket、源码及日志，并映射多个端口；不得直接用作生产 Compose。
3. 优先将执行容器放在独立节点/独立 Docker 引擎。调度器控制 Docker 的权限等同高权限基础设施操作，不能把 socket 挂到普通业务容器。
4. 后端 `BUILD_SERVER_URL`、`AI_AGENT_URL`、`DOCKER_PROXY_URL` 必须指向实际服务；还要核对后台沙箱配置对环境变量的覆盖。
5. 逐项验收租户/空间路径隔离、创建项目、真实生成、SSE、预览 WebSocket、发布、停止、重启后文件保留。接口健康不能替代以上验收。
6. 不对线上全部旧任务盲目重试，不把数据库状态直接改为成功。

## 在线更新入口

新增 `deploy/offline/update-online.sh`，在服务器运行已审查的本地脚本；下载内容仅作为 JSON 数据，不下载并执行远程 shell。

```sh
sh update-online.sh /path/to/deployment https://releases.example.com/update.json TRUSTED_SHA256
```

最后一个参数必须是经可信渠道取得的清单 SHA256，而不是从同一未认证来源自动信任的值。HTTPS 不能代替发布者签名；后续接入签名清单和防降级策略。

清单遵循现有 `update.sh` 格式：`mode=online`、发布版本、`schemaUnchanged=true`、`dataBackwardCompatible=true`，frontend/backend 使用 `repository@sha256:digest`。
入口限制 HTTPS 与 HTTPS 重定向、下载体积及超时，校验后复用本地更新器。

当前只更新前后端，不自动更新 MySQL、MCP、RCoder 或数据库结构。保留配置和数据卷，备份数据库，健康失败恢复旧镜像。
允许原有前端只读 `/etc/nginx/templates/default.conf.template` 挂载，其他前端源码挂载及全部后端 bind mount 仍拒绝；更新不会修改该模板。
镜像拉取复用 Docker 已有层，实现传输增量。不要在运行容器内覆盖程序文件来冒充镜像版本更新。

后续管理端更新功能需要：平台管理员专属授权、审批和审计、独立受限更新代理、发布源签名、执行锁、进度、失败回滚。不能把 Docker socket 挂到网页后端，也不能接受用户任意镜像地址或 shell 命令。

## 发布门禁

- 生产发布前备份 Compose、环境配置和数据库，记录当前镜像 ID；不改既有多租户开关。
- MCP 至少验证一个真实工具调用，再逐一验证现有服务。
- 沙箱和网页应用全链路未通过前，不宣称恢复。
- 在线更新需先确定仓库与可信发布源，在测试环境演练一次失败回滚后再启用生产。

## 本地服务接入（2026-10-09）

在 `C:\Users\zhang\nuwax` 下执行，要求已有 `singux-local_default` 网络和本地后端。不要在生产服务器执行这些本地脚本。

```powershell
docker compose -f deploy/services/compose.local.yml up -d
python deploy/services/connect-local-backend.py
python deploy/services/register-local.py
python deploy/services/prepare-checks.py
python deploy/services/check-local.py
./deploy/mcp/test-recovery.ps1 -base http://127.0.0.1:18022 -Container singux-services-local-mcp-proxy-1
```

登记脚本交互读取本地管理员密码，不保存密码。仅创建/更新 `singux-local-agent` 和 `singux-local-page` 两项配置，不重置用户或修改已有其他沙箱。

预览入口 `http://127.0.0.1:18093/login`。文件服务诊断端口 16000，调度端口 8086，代理诊断端口 18088，MCP 诊断端口 18022，均仅绑定回环地址。诊断接口不是公网用户入口；无鉴权的直接 noVNC 地址只用于本机测试。

文件保存在 `singux-services-local_workspace` 命名卷：`projects`、`computer`、`templates`、`uploads`、`dist`、`logs`。不执行 `down -v`、卷清理或覆盖旧项目。调度器自动清理闲置执行容器，不代表可删除工作目录。测试登记的 Project 隔离要求 pod_id 与项目 ID 一致；不可任意指定另一 pod_id 后仍期待原项目目录被挂载。

本地后端连接前的容器保留为 `singux-local-backend-1-before-services`，不自动删除。镜像不变、数据库不迁移。上线前还需独立备份数据并演练回退，不能直接复用开发机容器命名与网络。

已验证基础设施、模板复制、文件共享/持久化、桌面 WebSocket、MCP 工具调用。真实模型授权、完整网页生成/预览/发布、登录后的电脑权限和技能同步仍需业务验收，不能以 health 或该检查脚本代替。

`prepare-checks.py` 会创建固定名称的本地测试项目、ensure 三个验收容器，并安装模板依赖/启动 Vite；不是只读操作。`check-local.py` 则只检查这些验收对象。RCoder 重启时执行容器可能被回收，须重新 ensure，原卷目录仍保留。

本地网关 `/proxy/4000-4999/` 对接这一版文件服务内的 Vite，不转发到 Agent 容器；使用固定 Host `localhost` 避免 Vite Host 校验拒绝。超过该端口范围需显式扩展已验证路由，不任意代理用户指定地址。14000 只映射第一项测试项目（4000），用于浏览器诊断，不作为正式多用户入口。

## Linux 服务部署与回退（2026-10-09）

生产部署工具位于 `deploy/services/`：`ship-images.py` 固定 SSH 指纹、导出已测试的四个镜像、断点上传并核验 SHA256；`prepare-production.py` 生成 Linux 网络和限额配置。`deploy-runtime.py` 在服务器导入镜像并启动独立 `singux-runtime` 项目，不替换现有平台容器。首次执行拒绝覆盖已有部署和非空工作目录，失败保留工作文件并停止新增服务。

服务器运行配置目录 `/data/singux-update/services-runtime-20261009-r1` 包含 Compose、私有调度密钥和 Nginx 配置。该目录在运行容器中存在只读配置挂载，不能当作无用上传包删除。密钥文件只允许 root 读取，不应加入 Git 或分发到客户端。

新工作文件保存在 `/data/singux-services/workspace`。诊断端口 16000、18096、18088 只监听服务器回环地址；调度 API 开启 API Key，执行容器使用独立 `singux-execution` 网络、不挂 Docker socket、不公开容器端口。调度器自身挂 Docker socket，是高权限内部服务；共享文件服务也不是强多租户文件隔离，本次保持原单租户版本。

接入脚本 `connect-production.py` 先备份现有配置、SQL 和沙箱列表，再通过管理员 API 登记 Agent/PageApp，最后仅调整后端服务 URL。后端镜像和数据挂载必须与旧容器一致。沙箱初始禁用，连通和后端健康检查通过后启用。失败回退后端配置并撤销本轮登记，不恢复数据库、不删除用户数据。

接入之后，平台维护命令必须带上所有叠加文件，不能只用原 `compose.json`：

```sh
cd /home/singu-x-1.1.10-20260924-r1-linux-amd64
docker compose -p singux --env-file .env -f compose.json -f compose.mcp.json -f compose.runtime.json -f compose.filing.json ps
docker compose -p singux-runtime -f /data/singux-update/services-runtime-20261009-r1/compose.runtime.json ps
```

`connect-desktop-route.py` 将 `/computer/` 转到后端 18085 的鉴权代理，检查 Nginx 配置后平滑 reload；不直接公开 noVNC。原模板和生成配置保存在本轮备份目录。恢复该路由需恢复备份模板及生成配置并执行 `nginx -t`，通过后 reload。

若停用新功能，先在平台管理页禁用本轮两项沙箱配置；原平台使用不含 `compose.runtime.json` 的旧 Compose 组合重建后端，可撤销本轮 URL 变更。然后对独立运行项目执行 `stop`，不能使用 `down -v`、卷清理或删除工作目录。正式回退前检查当前镜像，避免回退掉后续的新版本。

电脑每容器 1.5 GiB RAM、总 RAM+Swap 3 GiB、1 CPU、256 进程；网页执行容器 1 GiB RAM、总 RAM+Swap 2 GiB、1 CPU、256 进程。闲置回收设为 10 分钟。平台每种沙箱 `maxUsers=1` 和 `maxAgentCount=1`，但原后端容量统计不是原子的全局准入锁，不能保证并发突发下只启动两个容器。当前 8 GiB 物理内存加 Swap 只用于低并发试运行，仍需监控内存和 OOM。

`verify-production-runtime.py` 创建固定名称的测试项目，验证模板共享、执行容器限制及私有电脑 WebSocket，测试后停止并移除本轮测试容器，保留测试目录。基础设施验收不代表真实模型授权、用户登录后的全部电脑权限、技能同步或网页生成发布已经通过。

### 新服务器迁移暂存（2026-10-09）

2026-10-11 目标 HTTP 入口变更：`compose.app.test.json` 前端宿主机端口现为 `8000:80`、`8080:80`，不再发布宿主机 80。仅重建目标前端，其余容器未重建；内部容器端口和网络隔离不变，本机 8000/8080 登录页均通过。访问 `http://113.219.170.192:8000/login`，不要使用 HTTPS；需要云安全组独立放行 TCP 8000。首次公网检查仍超时，未标为公网完成。备份及结果在 `http-port-8000-20261011`；回退只恢复端口字段并单独重建 frontend，不整份覆盖后续 Compose，不停止数据库。下文旧“发布80/8080”是历史状态，以此为准。

2026-10-11 旧官网紧急恢复（不是目标迁移操作）：源 `/data` 写满，活动后端日志约 20 GB，MySQL binlog 无法写入，导致业务接口失败及页面空白。`recover-source-log-space.py` 固定源主机/Compose 身份，将日志范围归档到系统盘、解压 SHA256 校验，再以 `fallocate --punch-hole --keep-size` 释放已归档块。原活动文件逻辑大小不变，因此不要仅用 `ls -lh` 判断释放失败，要检查 `du` 和 `df`。归档及范围结果保存在 `/root/singux-log-recovery-20261011`，含可能敏感的历史日志，保持目录 0700、文件 0600，不公开或随迁移包分发；重复执行已完成步骤直接返回，不重新归档已打洞的零区间。

首段已释放 2 GiB，剩余操作以 `remaining-result.json` 完成状态为准。登录、用户、空间 API 成功，实际首页列表重新显示。备案更正为“蜀ICP备2026053509号”：旧前端在线 HTML 原子替换，Compose 持久化镜像已更新，运行容器未重建；回退时只核对本次 HTML/镜像字段，不整份覆盖其他后续配置。后端日志大小限制仅在 D 盘源码修改，用户已要求稍后维护、暂不重启，因此运行中仍是原按天轮转，须在下次维护部署日志配置。无数据库恢复、数据删除、源写入暂停、DNS 切换或新增定时任务。

本轮完成结果：`result.json` 与 `remaining-result.json` 均为 `LOG_PREFIX_ARCHIVED_AND_DEALLOCATED`，两段归档合计 21,359,104,000 字节，解压 SHA256 均通过；`/data` 恢复约 20 GB 可用、使用率 81%，`du /app/logs` 约 71 MB，系统盘约 30 GB 可用。归档完成后不要把日志文件的稀疏逻辑长度当成实际占用再次归档；保留范围报告和压缩包。长期容量限制未部署，尚未完全消除复发风险，须在维护窗口完成，不自动重启或建立清理定时任务。

2026-10-10 17:10/17:11 北京时间刷新增量审计：两端私有 `reconciliation-20261010/refresh-20261010t0912` 保存新的只读摘要，未覆盖原摘要。源 113 表/162,109 行、目标 111 表/60,218 行，两端用户各 190；新增源自定义表 `custom_table_18`、`custom_table_19` 暂为空。公共表列元数据未变化，但新表索引/约束及业务引用还需审查。结果 `THREE_WAY_SCHEMA_REVIEW_REQUIRED`，没有应用任何 DDL/行增量，不继续使用旧 111 表结论作为当前可覆盖依据。

源知识库文档 219、原始分段 90,416，目标分别 125、1,996；文件记录 1,258/1,110。数据库增量必须关联上传文件、对象、全文/向量索引的新边界处理，不能以用户计数相同宣称全部数据最新。运行 `audit-migration-row-digests.py --run-id <新的小写字母数字连字符标识>` 创建新快照；同标识已完成时不重复，旧目录保留。比较工具 `--source/--target/--baseline/--output` 可显式指定，新输出必须不存在；报告仅含结构名与数量，不含用户原值或凭据。

2026-10-10 17:04 北京时间网页应用补验：正常登录创建个人空间临时 React 项目，模板、信息/文件读取、启动开发、鉴权预览 HTML、POST `/api/custom-page/keepalive` 五项通过，记录 `authenticated-webapp-verification.json`。没有 GET `/api/custom-page/dev-status` 路由；首轮因测试误用失败的报告保留。保活可能启动/维持进程，不可当作只读查询。未测试模型生成、发布或公网。

停止开发首次仍可能失败：文件服务只等待 100 ms 后检查退出，复验第二次 stop 成功，工具记录 `stopAttempts=2` 并最多重试三次。此容错不等于已修复服务端停止时序。临时项目已经正常 API 删除，首轮项目另行核对无残留进程，保留目录不强删；删除项目先删元数据可能使文件清理失去租户/空间隔离参数，待修。网页开发实际位于 file-server 进程空间，不能宣称已实现每项目独立容器隔离。其他迁移队列冻结、源数据及域名保持不变。

2026-10-10 16:49 北京时间智能体电脑补验：正常管理员登录后创建个人空间测试智能体/会话，发现原电脑镜像 healthy 但 VNC 状态永久 false。启动脚本的 5901/缺失就绪标记与引擎 5900/`/tmp/vnc_ready` 约定不符。仅目标构建 `singux/computer-runner:20261010-readiness-r1` 修正端口与实际就绪探测，确认没有执行中用户容器后更新 RCoder 私有配置三项镜像字段并重启该服务；未重启业务后端、数据库或源站。备份在 `desktop-readiness-20261010`，不要整份覆盖后续配置来回退，应核对镜像三字段。

`authenticated-desktop-verification.json` 为 `AUTHENTICATED_DESKTOP_VERIFIED`：普通登录 ensure、VNC ready、鉴权 HTML、匿名拒绝、鉴权 WebSocket 101、保活均通过。测试智能体221/222/223、会话965/966/967已正常删除，测试电脑已清理，工作目录保留。`verify-migration-user-desktop.py` 完成时不重复创建；失败必须检查清理记录后显式 `--retry-cleaned-failure`，保留旧报告。尚未验证公网浏览器画面及真实模型执行，不能将协议验收标为全平台上线。

2026-10-10 16:29 北京时间三方基线审计：原始 SQL 校验后仅恢复到独立、无网络的审计 MySQL，111 表/60,201 行生成摘要，随后停止审计容器；业务 MySQL 未恢复或重建。审计容器及专用卷 `singux-migration-baseline-audit-20261010` 保留，不能当成业务数据库启动。`reconciliation-20261010/baseline/result.json` 为 `BASELINE_DIGEST_VERIFIED`；已完成时工具直接返回，不重复导入。

基线与既有 06:42 两端摘要分类结果 `migration-three-way-audit-20261010.json`：源单端新增318/更新334/删除76，目标单端新增2/更新2，双端不同修改20（含18条任务冻结）、新建主键碰撞5（操作日志）。这是历史独立快照，不是当前同步结果；不执行变更 SQL，不自动删除/覆盖。后续增量必须刷新摘要并复核字段策略、关联键和外部文件/索引，不覆盖目标冻结锁及日志，不因用户登录时间差异重置密码。源服务不变、域名不变。

2026-10-10 16:19 北京时间模型补验：目标已更新 `singux/backend:1.1.10-20261010-model-routing-r1`，仅修复模型工厂将直连凭据误发内部代理而导致配置测试 403 的问题，MCP 日志补丁保留。源码回归同时覆盖代理/直连的普通及流式响应，目标内网合成 OpenAI 上游实测通过配置 SSE、授权 JSON/usage、授权中文 SSE 和无效 Key 拒绝。结果 `model-contract-verification.json` 为 `MODEL_CONTRACT_VERIFIED`，明确 `syntheticUpstream=true`、`realProviderVerified=false`。临时模型和 Key 已清理、监听已关闭。指定模型 API 路径为 `/api/proxy/model/{id}/v1/chat/completions`，不要省略 `/v1`。源站未部署这个修复，真实外部模型和公网仍未通过，不能把合成协议验收等同真实智能体业务验收。

2026-10-10 MCP 日志补丁已同步目标：镜像 `singux/backend:1.1.10-20261010-mcp-logs-r1`，仅两个 MCP 模块变化，环境/卷/其他服务 ID 不变，回滚材料在目标 `mcp-logging-20261010`。实际失败日志查询通过，临时服务 80、81（首次失败测试）和 82、83（复验）均已清理。首次失败原因是日志刷盘任务也被迁移冻结：仅恢复内部 `logApplicationService`，原锁保存在 `log-worker-before.json`；结果 `log-worker-result.json`。其他原恢复任务仍冻结，后端仍仅内部网络。后续任务冻结校验须明确排除这个已审查的内部日志任务，不能整体恢复原锁。日志流增加目标诊断事件，因此原 ES 导出快照摘要属于恢复时验收，不等于目标索引现在仍逐字相同。

当前可查看本地进度 `http://127.0.0.1:18108/`。公网 80/443/8080 再次直连均超时；不要通过公开数据库、调度器或 Docker API 绕过网络问题。新日志补丁通过不代表公网、完整模型调用、源后续增量或最终切换已完成。

2026-10-10 06:57 北京时间字段补验：对 19 张表、361 条已变化的公共主键记录比较字段摘要。3 条用户仅登录/更新时间不同；5 条日志同主键不同事件内容，不可覆盖。知识库分段及任务仍在源站继续变化，必须保留目标冻结设置并重新取增量边界。报告 `outputs/migration-field-differences-20261010.json` 只包含列名与数量，不含凭据或字段原值。进度页中的“增量审计快照”有固定时间，不是实时同步完成状态；本轮没有应用任何增量。

2026-10-10 增量盘点：两端 111 张业务表结构一致，82 张内容一致、29 张有差异；源 60,448 行、目标 60,208 行，两端用户均为 190 条。结果 `INCREMENTAL_ROW_DIFFERENCES_AUDITED` 保存在 `outputs/migration-incremental-audit-20261010.json`，服务器私有目录 `reconciliation-20261010` 保留行摘要。仅执行只读一致性事务，没有应用增量。源端后续写入、目标验收数据及任务冻结设置必须结合基线分类；目标独有行不等于可删除，公共主键内容不同不等于可覆盖。不得整体恢复旧 SQL 或解除定时任务冻结来消除差异；两次独立快照不是跨存储一致性证明。

2026-10-10 重启持久化补验完成：目标 `vector-persistence-verification.json` 与 `vector-content-verification.json` 的最新状态均为 `VECTOR_RESTART_PERSISTENCE_VERIFIED`。仅重启目标 Milvus，容器 ID/挂载不变，32 集合、3,764 行逐字段/向量比对及 8 项限定主键检索再次通过；没有重新导入数据。此前“尚未做重启验收”是历史状态。源 `kb_18` 的计数差异仍保留，真实新文本嵌入、受控模型出站、公网与源后续增量不在该验收范围。工具 `verify-migration-vector-persistence.py` 的完成状态会阻止重复重启；不要删除结果文件绕过保护。

最新补验：`upload-permissions-result.json` 为 `UPLOAD_PERMISSIONS_REPAIRED`。Java 用户 UID/GID 为 999，原恢复卷 root/0700 会令真实上传失败。权限修复工具只操作已核对的 `singux_backend-uploads` 卷，原权限保存在私有 `uploads-permissions-before.json`，1,109 个恢复文件摘要不变。不要重复运行该首修工具或 chmod 777。`app-auth-result.json` 当前为 `APP_AUTH_UPLOAD_CHECKED`，管理员上传/鉴权下载 51 字节回读一致；验收脚本每次会保留一个小型测试文件，不应当作定时健康检查反复执行。

`vector-content-verification.json` 为 `VECTOR_CONTENT_AND_SEARCH_VERIFIED`：32 集合/3,764 行，全部非向量字段精确比对、向量逐分量相对容差 1e-5/绝对容差 1e-6 验证，8 个非空集合的指定主键 COSINE 搜索通过。源 `kb_18` 差异未消除，未做新文本嵌入及重启持久化验收。公网复核发现目标 UFW 未启用、INPUT ACCEPT，但旧服务器也无法访问新 IP:80；需要确认公网入口映射/云安全规则，不要为绕过阻塞公开数据库或控制接口。

2026-10-10 平台已启动：目标使用 `compose.app.test.json` 启动 backend/frontend/MCP；独立 runtime 使用 `/data/singux-update/services-runtime-20261009-r1/compose.runtime.json`。五个基础服务使用 `compose.infra.json`，MySQL 仍为独立 `compose.mysql.json`。维护时分别查看各配置，不用源四份文件覆盖目标，不能执行 down -v。目标前端发布 80/8080，backend 仍在内部隔离网络。

目标 runtime 的 `network_base_name` 已从 `singux-runtime` 修正为 `singux-execution`；原私有配置备份在同目录 `rcoder.before-network-fix.json`，含密钥不得分发。测试结果 `runtime-verification.json` 确认网页模板共享、电脑限制/网络及 noVNC/WebSocket，通过后已清理本轮测试容器。首次恢复工具不能再次盲跑覆盖工作目录。

`app-auth-result.json` 确认登录、当前用户和主要列表成功；目标本机 HTTP 正常。公网 80/8080 从本地均超时，需检查主机/云防火墙和公网映射，不能宣称公网通过。临时本机 SSH 通道 `http://127.0.0.1:18109/login` 用于查看目标，不是旧官网也不改变 DNS。仅开放必要 HTTP/HTTPS，不能公开 MySQL、Redis、ES、Milvus、Docker socket、RCoder 管理口。出站隔离仍阻止真实模型调用，后续需设计受控出站及更完整的 standby 后台任务开关；未经增量协调不切换正式域名。

2026-10-10 最新实测：完整镜像归档两端 SHA256 `20fd47e45a07f9db9db517765b628372628b432c68a1e353ec95c8e48aa2e8d4` 一致，14 个镜像 ID 校验通过。`start-migration-infra.py` 已完成五个基础服务的实际 API/PING 检查，`infra-start-result.json` 为 `INFRA_READY`，MySQL 容器保持不变。不要重复执行首次启动检查工具；日常状态读取结果及容器即可。

MinIO 实际恢复结果为 `MINIO_EXPORTED_OBJECTS_RESTORED`，93 对象全部回读摘要一致；ES 为 `ELASTICSEARCH_DOCUMENTS_RESTORED`，两个索引共 2,420 条文档逐项内容比对一致。Milvus 为 `VISIBLE_VECTORS_RESTORED`，32 集合/3,764 可见记录，flush/load 后主键集合核对通过；`kb_18` 原导出差异仍保留，真实检索、完整向量内容和重启持久化另行验收。下方“尚未恢复”属于此前阶段历史记录，以最新结果文件为准。前后端真实业务验收未完成，DNS 不变，源写入后的增量仍需协调。

已核对源四份叠加 Compose 的解析配置及独立 runtime：backend 通过 `singux-service-gateway`、`singux-file-service` 别名调用运行服务，frontend 将 API/模型代理分别转发 backend 8081/18086。目标须保留这些私网别名与原鉴权配置，前端只读模板挂载改为目标已有文件。`CODE_EXECUTE_URL` 和 `LOG_SERVICE_URL` 仍是 `host.docker.internal`；不得将其认作目标已运行依赖，不应为了“接通”暴露 Docker socket 或未鉴权执行端口。

目标 `compose.app.private.json` 已生成且 Compose 校验通过，`app-preparation-result.json` 为 `PRIVATE_APP_CONFIG_PREPARED`。仅三项业务服务配置，无端口，仅内部网络；显式使用现有 `singux_backend-uploads` 外部卷，不含 MySQL，不会执行旧数据库种子 SQL。前端模板挂载已映射到目标实际文件。尚未执行 up；下一步准备独立 runtime 的配置与工作目录，核对后台队列和新任务风险，再私网启动业务并逐项验收。不要直接照搬源的全部配置执行 up 或将此准备状态视为已上线。

目标上传卷已实际恢复：`singux_backend-uploads` 含 1,109 个文件、250,158,735 字节，`uploads-restore-result.json` 为 `UPLOADS_VOLUME_RESTORED`，全部文件 SHA256 和清单一致。不要重新运行首建工具，它拒绝已有卷；后续使用该卷，不挂空路径覆盖。尚需检查运行后端 UID/GID 和实际下载访问。

MinIO 恢复脚本已上传目标 `restore-migration-minio.py`，1 桶、93 对象的离线预检通过，尚未恢复。使用临时 MC_HOST 环境传入鉴权，不保存 alias 密钥；首次拒绝与已有对象冲突，`--resume` 仅针对 `MINIO_RESTORING` 检查点。每个导出对象恢复后从 API 回读验证 SHA256；其他新目标对象保留，不执行 mirror --remove。`a-bucket/files` 为历史 Milvus 存储，仍须另跑向量逻辑重建，不能只复制这些对象后宣称集合可用。桶版本历史、策略和完整业务访问尚未验收。

全文恢复工具已上传为目标 `restore-migration-elasticsearch.py`，两个索引共 2,420 条导出已预检通过，尚未连接运行 ES 写入。基础服务可用且 backend 未启动时执行首次恢复；中断只在结果 `ELASTICSEARCH_RESTORING` 时显式 `--resume`。工具检查每条 bulk 响应、计数，并 mget 比对全部原文 source；源 UUID/version/creation_date 等不得传给新建索引，其他映射和 ID 保留。源索引 3 分片/1 副本在单节点上可能 yellow，需核查主分片可用、计数和内容，不删除数据来修复副本状态。

已用 `freeze-migration-queues.py` 在目标备份 `target-queue-original-locks.json` 和 `target-queues-before-freeze.sql.gz`，冻结 20 条已有待执行任务的时间至 2099 年，重试候选 0 条；原状态不改。结果 `queue-freeze-result.json` 已验证，无到期旧任务。该操作不影响源端，不全局禁止后续目标新任务；正式切换前须按原值与最新源数据逐项协调，不能直接导入备份 SQL 重建表，也不能自动解冻造成双端执行。

向量恢复脚本 `restore-migration-vectors.py` 已编写，尚未实机执行。目标五个基础服务运行后上传并运行（仅新库、无 backend，内部网络）。首次拒绝已有未登记集合；中断时先检查 `vector-restore-result.json`，只有 `VECTOR_RESTORING` 才可显式 `--resume`。按显式 ID upsert 后 flush、加载并逐集合比对可见主键集合，保留原 kb_18 警告；API/schema 构造单测不等于实际恢复或持久化验收。全文索引、MinIO 对象和上传卷仍需独立恢复。

工作区已进一步安全解包到目标 `workspace-staged/workspace`，242,200 项。`workspace-staging-result.json` 为 `WORKSPACE_SAFE_STAGED`：5 个旧 Chromium 临时 Socket 链接已隔离，配套 10 个旧浏览器锁/Cookie 符号链接只从暂存副本移除，完整原归档保留。尚未挂载到运行服务，仍需按服务 UID/GID 检查访问权限。目标 `compose.infra.json` 已生成并通过 Compose 配置校验，仅包含五个内部基础服务；镜像全部导入并校验后才可执行 `docker compose -p singux -f /data/singux-migration-20261009/compose.infra.json up -d --pull never`。该配置不含 MySQL，不改变已有 MySQL 容器。

重要：实际业务队列是自建线程轮询，`schedule_task` 按 `lock_time/status` 执行、`pf_retry_data` 按 `lock_time/status` 重试，`SPRING_QUARTZ_AUTO_STARTUP=false` 不足以停止它们。克隆后端启动前必须处理目标队列的重复执行风险；不能只阻断公网就宣称不会修改目标数据或执行内部任务。冻结目标队列前备份原行和值，源端保持不变，正式切换时单独制定恢复和增量策略。

自动续跑已完成核心业务文件暂存：源/目标业务归档 SHA256 一致，目标 `/data/singux-migration-20261009/business-staged` 包含 `business-export`、`backend-uploads`、`singu-download-site`，共 1,530 项。仅独立目录解包，不等于恢复到服务。工作区 242,205 项尚在完整原归档中；依赖符号链接需按目标目录安全验证，不能直接 root 解包覆盖 `/data`。镜像仍传输时可继续编写并校验恢复配置，不要重复传包或重复初始化 MySQL。

下一阶段读取暂存 `business-export/configs/platform-resolved.json`，根据 `images.json` 验证镜像 ID 后先启动内部 ES、etcd、Milvus、MinIO、Redis；已有 MySQL 使用原 `compose.mysql.json`，不重建其数据。原平台 MySQL 的 bind 初始化 SQL 应移除，前端代理模板使用已解包的新路径。默认网络已是隔离的 `singux_default`，不要因源配置默认网络未标 internal 而重建它。恢复对象/索引后验证计数，再处理 backend、frontend 与独立 runtime 的接入；仍须防止克隆后台任务重复执行。

2026-10-10 数据库实测恢复成功：目标 `singux-mysql-1` healthy，`agent_platform` 97 张表、`agent_custom_table` 14 张表、用户表 190 条记录。镜像 ID 与 SQL SHA256 校验通过，`mysql-restore-result.json` 状态为 `MYSQL_RESTORED`，但 `targetPlatformStarted=false`、`laterSourceWritesIncluded=false`。归档生产者已恢复。该配置仅用于数据库优先恢复，不得将其作为全平台 Compose 直接上线；其他镜像、文件和索引恢复及登录验收仍未完成。

2026-10-10 核实：后台镜像和业务包仍未完整传输，目标此前没有运行容器，不能称为部署完成。现新增 `deploy/services/restore-migration-mysql.py`，在空目标上优先传输 MySQL 镜像并校验 ID，使用暂存 SQL 的原 SHA256 校验后恢复应用库。仅数据库的 Compose 配置是目标 `/data/singux-migration-20261009/compose.mysql.json`，使用私有网络、不公开数据库端口、不挂旧种子 SQL。完成状态保存在目标 `mysql-restore-result.json` 和本地 `outputs/migration-mysql-restored-20261010.json`；结果文件不存在时不得宣称恢复成功。

`pause-migration-bulk.py` 只暂停已登记归档任务的 tar/gzip/docker-save 生产者，保留传输会话与全部业务容器；最大 15 分钟，独立看门狗按 PID 启动时间恢复。前台核心恢复完成后应主动执行 `resume`，不要无限期暂停归档。数据库完成恢复也不等于前端、后端、文件和知识库完成部署，不能仅凭 MySQL healthy 切换 DNS。

目标 `113.219.170.192` 已完成 Ubuntu 24.04、100 GiB `/data` 数据盘、Docker 与 Compose 准备。Docker/containerd 均在数据盘。源 `43.136.175.19` 继续运行，用户要求不暂停写入；数据库使用在线逻辑快照，不能将它视为所有存储的同一时间点备份。

两端暂存目录均为 `/data/singux-migration-20261009`，权限仅 root。源端 `background-export-result.json` 和 `image-job.log` 记录后台镜像传输；目标 `background-images-result.json` 和 `receiver.log` 记录导入结果。只有双方 status 完成、SHA256 相同且镜像 ID 校验通过才算镜像暂存成功。脚本不启动平台、不切 DNS。未完成业务数据全量和增量同步、知识库索引与文件验收，不能直接切换官网。

MySQL 在线快照位于 `application-databases.sql.gz`，不包含用户导出后产生的写入；无需也不应复制运行中的 MySQL 数据文件来补增量。跨服务切换还需设计在线增量或协调最终同步。目标启动后台任务前须避免重复运行源端任务、回调或通知。旧容器、卷及现有域名不得清理。

### 备案页脚补丁（2026-10-09）

生产已增加第四个叠加文件 `compose.filing.json`，仅覆盖前端镜像为 `singux/frontend:1.1.10-20261009-filing-r1`。平台后续 `up` 操作也须保留以上四个文件，避免覆盖 runtime 地址或回退备案页脚。停用 runtime 时仍需保留 filing 文件，不要照搬此前三文件历史命令。

补丁源文件位于 `deploy/compliance/`，云端工作目录 `/data/singux-update/filing-20261009-r1`，备份 `/data/singux-backups/filing-20261009T080611Z`。该版本只向原 HTML 外壳追加页脚和 CSS，不替换业务 JS，不迁移数据库。页脚覆盖平台单页应用路由，不修改第三方嵌入页面或生成的独立应用。

仅回退本次备案补丁时，先核对当前镜像及是否已有后续更新，再使用原 Compose、MCP、runtime 三文件执行 `up -d --no-deps --pull never frontend`，恢复原前端镜像；备案页脚随之移除。保留备份和 filing 文件供核验，不执行数据卷删除或数据库恢复。不要再次直接运行首次部署脚本，脚本会拒绝已有 filing 配置。
