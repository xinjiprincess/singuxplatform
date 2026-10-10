# Singu X MATE 项目说明书与 AI 开发交接

交接日期：2026-09-26。接收方：使用 DeepSeek 的 Claude Code，亦适用于其他开发者。

本文帮助接手当前代码，不代表全部功能已完成，也不是生产操作授权。开始执行前重新读取源码、工作区差异和本机运行状态；历史测试记录不能替代你这次的验证。不要把项目名中的 Agent 系统与执行任务的 Claude Code 混为一谈。

## 1. 你的任务

在现有 Singu X 平台上完成多企业登录与多租户改进，优先交付真正的“登录 -> 选择企业 -> 进入企业工作台”流程，随后按阶段完善企业生命周期、成员、全链路隔离、品牌与 Caddy 域名能力。

权威需求文档：`C:\Users\zhang\nuwax\docs\multi-tenant-v2-plan.md`。其中接口和页面若注明“拟新增”，就不是已存在的功能，不要直接调用假定它有效。

明确保留用户已确认的要求：

- 一名用户可加入多家企业，每家企业的角色与权限独立。
- 主域名 `www.ciyuancenter.cc`，平台品牌 Singu X，默认中文，保留用户名登录。
- 企业选择属于登录流程，不只是工作台里的“我的企业”；未登录不公开全平台企业名单。
- 免费版禁止自定义 Logo 和自定义域名；额度首期预留且可由平台管理端修改，不宣称已有完整计量扣减。
- 使用 Caddy；本机 HTTP 与公共 HTTPS/客户域名证书是不同验收项。
- 微信支付和支付宝仅预留，不实现真实收款、退款、回调，也不生成假付款成功状态。
- 用户列表 CSV 导出已加入，继续完善权限和验证，不改成全企业数据下载。
- 镜像离线/在线更新入口已有基础脚本，数据库迁移必须独立设计。
- 每批更新 `VERSION_CHANGES.md`，明确已完成、已验证、失败和未完成项。

## 2. 唯一工作目录与文件入口

| 用途 | 绝对路径/说明 |
| --- | --- |
| 前端源码、构建、版本记录 | `D:\singuxplatform\x_frontend` |
| 后端源码、迁移、构建 | `D:\singuxplatform\nuwax-backend` |
| 完整方案 | `C:\Users\zhang\nuwax\docs\multi-tenant-v2-plan.md` |
| 开发约定 | 前端根目录 `AGENTS.md`、`CLAUDE.md`，以及目标目录内实际存在的局部约定 |
| 历史变更 | `C:\Users\zhang\nuwax\VERSION_CHANGES.md`，从上往下读，顶部最新 |
| 历史方案 | `docs/multi-tenant-plan.md`，已由 V2.0 替代 |
| 支付边界 | `docs/tenant-payment-reservation.md` |
| 本地网关说明 | `deploy/caddy/README.md` |
| 镜像更新说明 | `deploy/offline/UPDATE.md` |



本工作区已有大量未提交和未跟踪文件，包括品牌修复、租户代码、部署脚本。不要使用 reset --hard、checkout --、clean、全目录复制来“恢复干净”。先记录差异，再在现有变更上继续工作。不要执行 git add .：环境文件、数据库备份、大镜像包等不应提交。

## 3. 技术架构

| 层 | 当前技术/关注点 |
| --- | --- |
| 前端 | React 18、TypeScript、Umi Max 4、Ant Design/ProComponents、Less、Umi models、项目 i18n |
| 编辑与实时能力 | Monaco、AppDev Web IDE、SSE、直接 fetch/流式请求；这些不一定经过公共请求拦截器 |
| 前端测试 | Vitest、Testing Library；package.json 声明 pnpm 10.27.0，实际 CLI 版本需检查 |
| 后端 | Java 17 编译目标、Spring Boot 3.3.8、Maven 多模块；已执行过涉及 142 模块的构建 |
| 持久化 | MySQL，另有 agent_custom_table 自定义数据用途；不能只检查主数据库 |
| 其他存储 | Redis、Elasticsearch、Milvus、MinIO，以及本地 `/data/uploads` |
| 运行 | Docker Desktop Linux 引擎；本机 Caddy 入口 18090；正式服务器目标 Linux amd64 |

前端遵循现有 Pages/Components/Hooks/Services/Models/Utils/Types 分层，不新增无必要框架。服务层负责请求，类型放类型层；复用现有 Ant Design 和图标，不为选择页引入另一套 UI 库。新文字进入 i18n，命名遵循 AGENTS.md。

后端重点模块位于 `app-platform-modules/platform-system/` 的 system-spec、system-infra、system-domain、system-application、system-web；启动模块是 `app-platform-bootstrap/app-platform-web-bootstrap`。业务隔离还涉及其他模块和外部执行服务，不能只改 system 模块就宣布完成。

## 4. 当前实现状态

### 4.1 已有代码，但需要继续验证

| 能力 | 文件或类 | 状态 |
| --- | --- | --- |
| 用户名登录与品牌 | `src/pages/Login/index.tsx`、本地 Logo、SiteFooter 移除 | 应保留，不允许回退到邮箱强校验或 Powered by 页脚 |
| 平台租户策略 | `src/pages/PlatformTenants/`、`src/services/tenantPolicy.ts`、`TenantPolicyApplicationService` | FREE/PAID、额度预留、策略版本/原因及审计基础 |
| 独立平台权限 | `PlatformAccessService` | 明确用户 ID 白名单并检查角色，不把全体企业 Admin 当平台超管 |
| 本人企业和切换 | `src/pages/MyEnterprises/`、`tenantMembership.ts`、`tenantSession.ts` | 已有工作台内切换，不是登录选择页 |
| 成员与会话 | `TenantMembershipService`、`TenantSessionService`、`TenantMembershipController`、`AuthServiceImpl`、`AuthInterceptor` | 有成员版本和企业绑定 JWT 基础，未完成全部登录/续期/流式隔离 |
| 数据迁移 | 后端 `sql/migrations/20260926-tenant-policy.sql`、`20260926-tenant-membership.sql` | 成员迁移曾在独立临时 MySQL 中重复执行验证；未对现有运行库自动启用 |
| 用户导出 | `src/services/userExport.ts`、`src/utils/userExport.ts`、`src/pages/UserManage/index.tsx` | CSV 白名单、BOM、公式转义、最多一万条；非事务快照，独立导出审计未做 |
| Caddy | `deploy/caddy/Caddyfile.local`、`compose.local.yml`、公共域名配置 | 本机曾实际运行；公共证书及客户域名未验收 |
| 更新脚本 | `deploy/offline/update.sh`、`scripts/package-offline.cjs` | 仅兼容 schema 不变的镜像更新；有模拟测试，无真实生产更新证明 |

### 4.2 不要误判的关键差距

1. 后端 `TenantMembershipService.bindLogin()` 仍自动选原企业或 tenantId 最小的企业；这与新版需求不一致。
2. Login 成功回调立即保存 ACCESS_TOKEN、刷新用户、加载菜单并跳转，尚未有受限 IDENTITY 会话。
3. `src/app.tsx` 的 getInitialState 仅特殊处理 `/login`；直接新增 `/login/enterprises` 可能触发错误的业务初始化和跳转循环。
4. MyEnterprises 当前是工作台内路由，依赖工作台和能力开关；不能原样当登录第二步。
5. 原全局 USER_INFO/TENANT_CONFIG_INFO/token 缓存尚未完成系统性改造，清部分 localStorage 键不等于隔离。
6. 公共请求拦截器的代次检查不覆盖所有 SSE、fetch、Worker、轮询、iframe 和后台任务。
7. 原 UserManage 的账号删除/重置密码等动作与企业成员管理尚未彻底拆开；不能允许企业管理员删除多企业共享的全局身份。
8. 数据/文件/搜索/任务/API Key/外部执行服务全链路隔离未完成；不能仅检查 tenant_id 字段存在。
9. 租户策略与成员开关目前作为未开放能力处理：`PLATFORM_TENANT_POLICY_ENABLED=false`，`PLATFORM_MEMBERSHIP_ENABLED=false`。重新检查实际容器，不要仅凭文档改开关。
10. 类型检查历史有其他路径约 152 项错误。数量可能变化，先建立新基线；不要删除检查或修改配置来伪造通过。

## 5. 登录后空白问题的背景

本机出现过“页面有背景但没有菜单内容”：测试库只有部分菜单/资源且没有角色；`GET /api/user/list-menu` 成功但返回 []，用户列表返回 4033。

当时已备份本机测试库，通过现有受保护权限导入接口导入代码内置 `permission-1.4.json`。之后新会话菜单返回 10 个一级菜单，用户列表成功返回 1 个测试用户。浏览器控制连接当时不可用，因此截图/真实下载流程没有完成验收。

后续要求：企业创建有 PROVISIONING/READY/FAILED 状态，标准权限初始化可重试且有版本记录；空菜单、无权限、加载失败要有明确 UI。不要再以 HTTP 200 或容器 healthy 作为“界面正常”的证据。

不要每次启动全量导入权限模板，它可能覆盖匹配 code 的定制配置；新企业初始化和已有企业增量升级要分开。

## 6. 本机 Docker 的实际关系

以下是交接前已知运行关系，不是保证容器此刻仍运行：

- 入口 `http://127.0.0.1:18090/login`，Caddy 容器 `singux-local-edge-caddy-1`。
- Caddy 通过 `deploy/caddy/compose.local.yml` 启动，挂载 C 盘 `dist`，转发 API 到 `singux-local-backend-1:8081`。
- 后端容器使用旧名称的 Java 运行时镜像 `singular-origo-backend:local`，但只读挂载 D 盘最新打包 JAR。镜像名称不能证明运行的是旧业务代码，应比对挂载和摘要。
- JAR：`D:\singuxplatform\nuwax-backend\app-platform-bootstrap\app-platform-web-bootstrap\target\app-platform-web-bootstrap-0.0.1-SNAPSHOT.jar`。
- 后端配置挂载来自 D 盘启动模块 `src/main/resources/application-prod.sample.yml`，另有容器环境变量。
- 测试依赖为 `singux-local-mysql-1`、`redis-1`、`etcd-1`、`minio-1`、`milvus-1`、`elasticsearch-1`（均带 singux-local 前缀），数据卷同此前缀。
- 后端和依赖处于 `singux-local_default` 内部网络；Caddy 额外连接入口网络，仅发布回环端口。只有内部网络时曾出现 Caddy healthy 但宿主机端口不可访问。
- 旧 `singux-tenant-ui-preview-20260926` 预览已停止；它曾挂载 D 盘旧前端，不应再启动抢占 18090。
- 其他 `singular-origo-*` 或不相关项目容器、数据库和卷不要操作。

重要故障点：部分原测试容器的 Compose 标签/初始化 bind 路径仍引用已搬走的 `D:\singuxplatform\nuwax_frontend\...`。之前 docker cp MySQL 备份曾因此失败，而 docker exec 仍可用。不要照旧标签重新创建容器，也不要通过创建假源码目录掩盖问题。需先核对所有 Mounts 和卷、完成备份，再把测试 Compose 规范化到权威目录；重建时保留原卷和初始化语义。

首次需要迁移/隔离试验时，优先建立另一个明确命名的测试项目和新卷，不直接修改这套用户正在查看的环境。禁止 down -v、volume prune、删除原数据。根目录 docker-compose.yml 的默认项目不等于上述测试环境，不可盲目执行 up 来“修复”。

## 7. 第一批具体工作：P0/P1

不是从零重建整个项目。按以下顺序做，逐项提供实际证据：

1. 只读核对前后端路径、工作区差异、依赖、测试基线、容器与挂载；列出与本文不一致处。
2. 追踪密码、验证码和其他登录入口、token 刷新、路由守卫、菜单初始化；输出身份/企业会话改造清单。
3. 定义并实现受限 IDENTITY 会话：仅能查询本人企业、选择、邀请及退出，不得调企业业务。
4. 实现选择接口，校验有效成员、企业就绪、域名、并发代次、票据过期/单次消费及幂等重试。不能先给完整业务令牌再靠页面遮挡。
5. 新增 `/login/enterprises` 页面，独立于工作台菜单；同登录页中文品牌。0/1/多企业、加载、失败、过期、暂停均有明确状态；只有一家也确认进入。
6. 修改 Login、app 初始化、auth wrapper、类型与服务层；只有企业会话就绪后加载菜单、空间和品牌。旧登录接口不能成为绕过新版选择/会话约束的入口。
7. 工作台内切换复用同一会话生命周期，处理旧响应与多标签页；未完成的长连接隔离明确登记，不能跳过后宣称全量安全。
8. 修复空菜单错误呈现，加入企业权限初始化就绪检查；不能通过硬编码菜单或 Admin 放行来避免白屏。
9. 跑自动化与隔离测试库联调，再做浏览器实际点击、刷新、选择、进入、切换、退出；确认 C 盘产物和 D 盘 JAR 对应这批代码。
10. 更新 VERSION_CHANGES 和阶段验收记录，列明未完成项，再进入 V2.0 的后续阶段。

P1 可以在隔离开发环境展示，但对外开放企业业务前必须完成 V2.0 P3 的隔离门槛。不能为了让页面出现而直接开启服务器的两个开关。

## 8. 后续工作包

| 工作包 | 交付结果 |
| --- | --- |
| 企业生命周期 | 创建、所有者、初始化版本、停用/恢复、审计；初始化失败不可登录 |
| 成员与身份 | 邀请接受/撤销、角色变更、所有权转移、全局账号与企业成员接口分离 |
| 全链路隔离 | SQL/自定义表/Redis/文件/检索/SSE/任务/分享/导出/API Key/外部执行逐项清单与攻击测试 |
| 品牌和域名 | FREE 后端拒绝；PAID 资产归属、TXT、域名冲突、Caddy 签证授权、续期和解绑 |
| 额度与支付 | 额度配置和审计；实际计量分项后续做，支付继续 NOT_CONFIGURED |
| 发布与运维 | 可追溯镜像、独立 schema 迁移、备份恢复、健康与业务冒烟、灰度；不把模拟更新测试当真实演练 |

## 9. 命令与验证基线

下列命令是便于复现的参考，不要求为了符合文档而重装或升级整个工具链。先检查路径和工具版本，执行时明确 cwd。不要同时运行多个 Maven 构建。

### 前端测试

工作目录：`C:\Users\zhang\nuwax`。

```powershell
node node_modules/vitest/vitest.mjs run tests/userExport.test.ts tests/tenantPolicy.test.ts tests/tenantProfile.test.ts tests/tenantSession.test.ts tests/tenantMembership.test.ts tests/MyEnterprises.test.tsx tests/PlatformTenants.test.tsx
node --test tests/update-script.test.cjs
```

历史结果：第一组 24 项通过；更新脚本模拟 Docker 的 8 项通过。第二组不会操作真实 Docker，但会启动 Git Bash 并使用本机 jq；需核对工具依赖。Windows 上曾出现 pnpm exec vitest 找不到可执行文件，用上述直接入口成功，不要因此直接删除 node_modules 或锁文件。

### 前端生产构建

```powershell
$env:UMI_ENV = 'production'
$env:NODE_OPTIONS = '--max-old-space-size=8192'
node node_modules/@umijs/max/bin/max.js build
```

不要使用 development 配置去部署本机生产静态页，它可能指向外部 API。先核对最终 BASE_URL。现有 Caddy 正在挂载 dist，原地构建会有短暂资源窗口；后续改为独立构建目录、验证后原子切换，不把用户正在用的目录清空再长时间构建。

### 后端测试

工作目录：`D:\singuxplatform\nuwax-backend`。项目编译目标 Java 17；本机曾使用 JDK 20 编译 release 17。Maven 曾位于下列临时目录，可能被系统清理，应先检查；找不到时使用已配置的 Maven/JDK，不把缺工具误报成源码故障。

```powershell
$env:JAVA_HOME = 'C:\Program Files\Java\jdk-20'
$mvn = 'C:\Users\zhang\AppData\Local\Temp\singux-maven\apache-maven-3.9.9\bin\mvn.cmd'
& $mvn -B -pl app-platform-bootstrap/app-platform-web-bootstrap -am '-Dmaven.compiler.useIncrementalCompilation=false' '-Dtest=TenantMembershipServiceTest,TenantSessionServiceTest,TenantTokenTest,TenantPolicyTest,PlatformAccessServiceTest,TenantPolicyApplicationServiceTest,TenantConfigContextTest' '-Dsurefire.failIfNoSpecifiedTests=false' test
```

历史结果：指定后端测试 31 项通过，相关 142 模块增量构建成功，不等于全库所有测试通过。必要时依赖缓存完整可加 `-o`，不能在缓存缺失时坚持离线然后删依赖规避错误。

打包须在测试之后：

```powershell
& $mvn -B -pl app-platform-bootstrap/app-platform-web-bootstrap -am '-Dmaven.compiler.useIncrementalCompilation=false' '-Dmaven.test.skip=true' package
```

package 跳过测试不是测试通过；这里只用于已跑完测试后的产物打包。编译但没有重新 package 不会更新运行 JAR。挂载部署还需要按用户授权重启对应测试后端，并比对宿主/容器内 JAR 摘要、健康状态和实际接口。

### 运行状态与文件检查

```powershell
git diff --check
docker ps --filter name=singux-local
docker compose -f deploy/caddy/compose.local.yml config --quiet
```

涉及 D 盘编辑、Docker、子进程或网络的权限被工具拒绝时，走正常授权流程。不要关闭权限、安全软件或以别的工具绕过限制。不要打印完整 docker inspect 环境变量、.env、数据库密码或 JWT。

## 10. 最低验收矩阵

自动化与真实 API 测试至少使用 A/B 企业、A-only 用户、B-only 用户、A 所有者/B 成员的同一用户、无企业的平台管理员：

- 未登录无法查询私人企业名单；身份票据不能访问用户/空间/文件等业务 API。
- 0/1/多企业均能正确呈现，单企业不靠自动默认企业绕过选择。
- 伪造 tenantId、Host、资源 ID、过期票据、重复/并发选择不能得到额外权限。
- A 所有者切到 B 后没有 B 管理员权限；移除 B 成员不影响 A；旧刷新令牌和长连接不能持续保留 B 权限。
- 新建企业有菜单、角色和所有者；失败明确提示，不出现空白工作台。
- 旧 A 请求晚于切换返回不会污染 B，多个标签页保持一致的活动上下文。
- CSV 仅包含获授权成员和白名单字段，真实下载能打开；权限错误时不得导出半份成功文件。
- 免费用户直接调用 API 不能绕过 Logo/域名限制；未验证域名不能触发任意签证。
- 更新脚本不对 schema 变更版本执行自动镜像回滚，不删除卷；备份和恢复都有演练。
- 浏览器看到正确页面、API 返回正确业务码、实际容器加载新产物三者都核实；不能只给截图或只给 HTTP 200。

对完整隔离逐项引用 V2.0 第 9、15 节。外部服务没有源码或无法验证时标明受阻能力并保持关闭，不能用模拟响应证明真实隔离。

## 11. 不允许的做法

- 不操作生产服务器、DNS、真实证书或商户配置，除非用户明确授权该次操作。
- 不使用关闭鉴权、硬编码管理员菜单、匿名企业列表、客户端 tenantId 信任或宽松 Host 兜底来让演示“跑通”。
- 不把整个 user 对象返回公开接口；密码/令牌/模型密钥/SMTP 密钥不进入页面、URL、截图或日志。
- 不移除 LICENSE/必要第三方许可文件；界面品牌清理与许可证保留是不同事项。
- 不把源目录里的 NuwaxCli 协议枚举、Java 包名或持久化字段机械替换为 Singu X；协议兼容名称不等于界面推广文案。
- 不执行真实支付、自动发布镜像、自动推送仓库或开放 Docker 管理接口；网页后端不能挂载 Docker socket 实现更新按钮。
- 不在未备份核对的运行库执行迁移，不连续导入全部历史 update-*.sql；合并 init.sql 可能已包含历史变更。
- 不因测试难以通过而删除断言、放宽权限或隐藏错误；不擅自修复全部历史类型错误扩大改动。
- 不和其他 Agent 同时编辑同一前后端目录。接手时先确认原执行者已停止写代码，阶段切换记录清楚。

## 12. DeepSeek + Claude Code 接入说明

DeepSeek 官方提供 [Claude Code 集成指南](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code/) 和 [Anthropic API 兼容说明](https://api-docs.deepseek.com/guides/anthropic_api/)。官方文档有此接入路线，但这不证明本机具体 Claude Code 版本、模型和工具调用组合已测试通过。

本说明不安装 Claude Code、不修改全局模型配置、不写入 API Key。模型名称、端点和兼容设置以接手时官方文档及实际账号可用能力为准；先做只读文件/搜索/工具调用小测试，再授权编辑和构建。不要复制来历不明的代理或远程一键安装脚本。

使用该后端时，提交给模型的代码和工具输出会进入所选服务商的处理链路；遵循项目的数据使用要求。不要向模型发送 .env、数据库备份、真实用户列表或完整运行环境。凭据通过本地安全配置注入必要进程，不写到本文件、不提交 Git。

建议将其作为分阶段实现执行者，不把模型自评当安全审计。尤其是认证、跨企业查询、SQL 迁移和证书授权，应由测试证据和独立代码复核确认，不保证任何模型一次完成整个多租户改造。

## 13. 每批交付格式

结束一批时报告：

1. 本批完成了哪个工作包，实际修改了哪些文件。
2. 新/改接口、迁移和兼容策略；是否影响现有账号/数据。
3. 运行了哪些测试，数量及结果；没跑的原因；不复述历史通过数作为新结果。
4. 本机实际地址、容器和源码来源，浏览器/接口验证证据。
5. 已知风险和未完成项，是否满足下一阶段门槛。
6. VERSION_CHANGES 的对应记录，以及下一项可执行工作。

遇到上下文压缩或工具中断，先重读本文件、V2.0 和最新版本记录，不从旧 D 盘前端或最早部署历史重新开始。

## 14. 可直接给 Claude Code 的任务指令

> 先阅读 C:\Users\zhang\nuwax\PROJECT_HANDOFF.md、AGENTS.md、docs\multi-tenant-v2-plan.md 和 VERSION_CHANGES.md 最新记录。前端只改 C:\Users\zhang\nuwax，后端只改 D:\singuxplatform\nuwax-backend。先只读检查当前状态和已有改动，然后按说明书 P0/P1 实施受限身份会话、登录流程企业选择页、路由与菜单初始化及相关测试，通过阶段验收后逐步完成其余多租户改造。保留用户名登录和 Singu X 中文品牌；不要暴露匿名企业名单，不要关闭权限校验。微信/支付宝只预留，额度首期只配置预留。只使用授权的本机隔离测试环境，不操作服务器/DNS/真实支付，不删除已有数据或覆盖原改动。每批更新 VERSION_CHANGES.md，并明确测试证据和未完成项；不要把设计文档、模拟测试或容器 healthy 宣称为完整生产验收。
