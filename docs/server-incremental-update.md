# 服务器增量更新与背景配置

## 2026-10-08：用户执行更新完成，等待业务验收

用户提供的终端输出显示单租户知识库更新器返回 `UPDATE_OK`，前端、后端、MySQL 为 healthy，其余项目服务运行中。后端镜像引用为 `sha256:ffa3a2071cf6d9e0d07cc3a7865bec75b13d03aab5bafbd8f918b5108792281c`，前端维持原 entry-fix 版本。没有发布多租户/比赛入口或数据库迁移。

备份目录：`/data/singux-backups/knowledge-20261007T171040Z-482687`。保留旧镜像与备份，并将敏感备份安全复制到服务器之外。尚未确认真实恢复演练、原账号和文件完整性、模型调用以及生产知识库完整删除接口；请先用可丢弃测试库验收，不删除真实业务库测试。

下方“已准备”和其他未更新描述为此前阶段的记录。本轮没有再次远程检查，线上状态依据用户提供的输出。

## 已准备：生产基线知识库单租户补丁

`outputs/singux-knowledge-singletenant-20261007.tar.gz` 已基于用户导出并核验的线上 r2 镜像制作，不是本地多租户完整镜像。仅修复 Elasticsearch 客户端兼容和全文删除，不包含此文下方此前规划的数字账号兼容或租户迁移。

使用包内 `update-knowledge.py`，不要使用旧 `deploy-backend-r2.sh`：先上传、核验 SHA256、解压，在原部署目录对应参数下运行默认只读检查；只有维护窗口、恢复验证和检查通过后才能使用 `--apply`。详细命令、备份覆盖及回退限制见 `deploy/KNOWLEDGE_HOTFIX.md` 或包内 README。

该补丁本地构建、全文删除真实存储测试及更新器模拟测试通过，尚未更新服务器。脚本实际生产冷备份/恢复未经演练；请先完成独立备份或云磁盘快照与恢复验证，不将归档可读检查视为业务恢复保证。

## 2026-10-04：本次明确保持单租户

用户已确认：**继续单租户，只更新修复和用户导入兼容，不升级多租户，不增加企业选择。** 下文旧的“第一次升级比赛入口”章节仅保留历史参考，不是本次执行流程。

本次本地客户端 v0.1.1 默认用户名为工号/学号、初始密码为本人手机号；旧账号不重置密码。新增单租户配置，无需填写企业/租户 ID，不调用入企接口。手机号属于弱初始密码，不能当作长期安全策略，也没有宣称已实现首次强制改密。

### 当前交付状态

- 本地后端 `UserApplicationServiceImpl` 已移除新增/修改时禁止纯数字用户名的限制，保留已有用户名唯一与保留格式校验；增加数字用户名/他人手机号的双向碰撞检查，单租户登录遇到两个不同账号争用同一标识时拒绝登录。
- 配套 `NumericUsernameImportTest` 包含六项创建、登录及碰撞测试。本轮 Docker 引擎未就绪，尚未执行后端测试或构建可上线的后端镜像。客户端的构建验证不能替代后端验证。
- **没有连接或更新生产服务器。当前本地后端已混有多租户开发代码，不能把整个本地最新源码/测试镜像当成单租户修复包直接发布。** 需核实线上基线，在同版本源码上移植最小修复，再构建独立版本标签。

### 单租户发布步骤

1. 核对线上当前镜像、Compose 项目与挂载方式。先只运行下方只读命令，不公开 `.env` 或完整 inspect 配置中的凭据。
2. 从当前线上版本的源码建立修复版本，仅带入数字学工号兼容及其他已确认的单租户修复。保持旧的登录、菜单、路由和企业功能开关不变；本次补丁不需要执行多租户迁移 SQL，也不重设管理员口令。
3. 用生产备份的副本在本地/隔离环境测试：普通用户名、带前导零学号、手机号登录、手机号初始密码、错误密码、账号/电话碰撞、已有账号不重置、智能体基本调用。确认旧 schema 可启动，禁用不应存在的新功能入口。
4. 发布前暂停导入和其他写入，备份业务数据库、上传文件/对象存储、当前 Compose/.env，并保留旧镜像和版本记录。备份须可恢复；本步骤不通过清卷或重新初装实现。
5. 导出已验证的新**后端应用镜像**、校验 SHA256、上传并 `docker load`。在原 Compose 中只改 backend 的 image 引用，保留所有环境变量、端口和卷。若原 JAR 是 bind mount，必须单独处理版本化挂载，不能仅换镜像后误认为新代码生效。
6. 校验 Compose 后仅重建 backend，确认健康和登录，再选少量经授权的账号试导入。客户端更新和服务器更新彼此独立；更新 EXE 不会自动更新服务器。
7. 失败时将 backend 的 image/挂载恢复为记录的旧版本，再按同样命令重建。若已经导入新账号，数据不能靠换回旧镜像回滚；旧版本也可能不支持修改数字用户名，需要单独核对。不要自动恢复数据库覆盖期间新增数据。

以下是只读盘点命令（服务容器名以 `docker ps` 实际输出为准）：

```sh
docker compose version
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
docker inspect singux-backend-1 --format '{{.Config.Image}} {{.Image}}'
docker inspect singux-backend-1 --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}} {{index .Config.Labels "com.docker.compose.project.config_files"}}'
```

**新单租户镜像尚未产出，下面只是镜像已加载、备份完成且 Compose 已正确修改之后的执行模板，不要现在照抄升级。** 假设原项目使用 `.env`、`compose.json`，服务名为 `backend`，并且保留原项目名称：

```sh
docker compose --env-file .env -f compose.json config --quiet
docker compose --env-file .env -f compose.json up -d --no-deps --no-build --pull never --wait --wait-timeout 600 backend
docker compose --env-file .env -f compose.json ps
```

本轮通常不需要更新前端容器；只有确认旧网页还拦截纯数字用户名时，才基于线上单租户前端做对应修复，不替换为多租户前端。禁止运行多租户/比赛 seed SQL、旧初装 `deploy.sh` 或 `down -v`。

Compose 定向重建会保留挂载卷，`--no-deps` 避免启动关联服务，`--wait` 等待运行/健康状态，见 [Docker 官方说明](https://docs.docker.com/reference/cli/docker/compose/up/)。应用健康检查不等于业务已验收，仍须实际验证登录及导入。

## 本次范围

本次只构建及验证本机 Docker，不连接或修改 43.136.175.19。官网与专用入口各自配置登录背景、工作台/管理布局背景；表格和表单仍保留底色，避免图片影响可读性。

管理入口：`/platform/portals`。官网使用“官网背景”，比赛使用对应入口“编辑”。留空恢复默认，保存填写变更原因，刷新对应页面生效。不改登录方式或租户绑定，不允许任意外站 URL 或可执行 HTML。

本版使用站内图片路径，支持 `/logo/...` 或可匿名访问的 `/api/file/...`；带鉴权、临时签名的文件不适合登录背景。当前没有新增上传按钮。预览确认图片有效后再保存。

推荐把公开背景放在服务器持久目录 `/data/singux-branding`，只存经确认可公开的 PNG/JPG/WebP。通过前端容器只读挂载到 `/usr/share/nginx/html/logo/backgrounds`，配置路径如 `/logo/backgrounds/official-login-v1.jpg`。这时换图无需重建镜像；改图建议新文件名避免浏览器缓存。该挂载需要添加到实际 Compose 的 frontend.volumes，不能覆盖整个静态目录。不要在容器内部手工改图，重建后会丢失。

## “增量”含义

推荐发布带唯一版本标签的前后端镜像，服务器只替换 frontend/backend，保留数据库、Redis、MinIO、上传卷及原配置。镜像仓库 pull 会复用已有内容层，不是向运行容器覆盖 JAR/dist。离线 `docker save` 包包含所选镜像，并非真正的二进制差分。

本地候选标签：`singux/frontend:1.1.10-20260929-background`、`singux/backend:1.1.10-20260929-background`。是否完成构建与运行验收以 `competition-portal-debug.md` 最新记录为准。

## 第一次升级比赛入口：先核对，再迁移

此次不能直接使用旧 `deploy/offline/update.sh`：该脚本仅支持不变更表结构的版本。服务器可能仍是旧后端，不能假定已有本地的成员关系、权益、首次资料和比赛表。

1. 在服务器现有部署目录记录 `docker compose -f compose.json ps`、前后端镜像 ID、Compose 文件路径和版本；检查代码/JAR/dist 是否有 bind mount，避免新镜像被旧挂载覆盖。配置中有密码，不公开粘贴完整 `docker inspect` 或 `.env`。
2. 对照服务器实际 schema 与后端 `sql/migrations`，列出缺失迁移和依赖顺序。`20260929-portals.sql` 只新增入口/审计表，不代表此前租户迁移已执行。禁止运行本地专用 `20260929-portal-local-seed.sql` 到生产，它假定本地管理员和默认租户 ID。
3. 安排维护窗口，停止应用及外部写入任务。备份全部业务数据库、上传文件/对象存储、Compose 和 `.env`，保留旧镜像；记录并验证恢复位置。
4. 按审定顺序执行缺失迁移，在服务器真实默认租户/平台管理员基础上初始化比赛租户、成员和权限模板。核对 `PLATFORM_PORTALS_ENABLED`、成员关系及租户策略开关、平台管理员 ID、受信任代理和允许域名；不能照搬本地环境变量。
5. 网关保持官网根路径，`/zhichuangbei` 交给同一前端 SPA，不剥掉浏览器中的前缀；`/api` 仍走后端，保留正确 Host/Origin。公开图片路径需匿名可读。HTTPS、业务 API、流连接配置保留原生产要求。
6. 加载或拉取已验证的两个新镜像，修改现有 Compose 的 frontend/backend image，并移除已确认过时的源码覆盖挂载。仅重建这两个服务，其他服务不升级、不清卷。
7. 检查健康、官网登录/企业选择、比赛固定租户登录、管理保存及背景资源 HTTP 状态。生产不得运行会临时停用比赛入口的本地测试脚本。
8. 失败时恢复旧 Compose/配置与旧镜像。增量兼容表通常可以暂留；若涉及数据转换，应按经过验证的备份恢复流程处理，不能自动覆盖升级后产生的新数据。

## 镜像传输命令

本地构建验证通过后可导出应用镜像（不包含数据库/上传文件）：

```powershell
docker save -o singux-app-background-images.tar singux/frontend:1.1.10-20260929-background singux/backend:1.1.10-20260929-background
Get-FileHash singux-app-background-images.tar -Algorithm SHA256
```

传输并通过可信渠道比对 SHA256 后，在服务器加载：

```sh
docker load -i /home/singux-app-background-images.tar
```

完成上述迁移和 Compose 修改后，在实际部署目录执行（此处假设仍使用 compose.json/.env）：

```sh
docker compose --env-file .env -f compose.json config --quiet
docker compose --env-file .env -f compose.json up -d --no-deps --no-build --pull never --wait --wait-timeout 600 frontend backend
docker compose --env-file .env -f compose.json ps
```

不要 `down -v`、不要删除旧数据卷，也不要重新运行旧包初装 deploy.sh。正式在线分发需先有自己的镜像仓库和不可变 digest；当前未发布在线更新版本。

上述 `--no-deps`、`--wait` 和保留挂载卷的重建行为见 [Docker Compose up 官方说明](https://docs.docker.com/reference/cli/docker/compose/up/)。

完成首次迁移后，后续经审查数据库不变且数据兼容的版本可使用现有 `deploy/offline/update.sh` 和 `UPDATE.md` 中的清单流程。不同生产部署结构不能强套该脚本。
