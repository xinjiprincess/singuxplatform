# 2026-09-28 本地修改清单

## 唯一工作目录

- 前端、部署配置、说明文档：`C:\Users\zhang\nuwax`。
- 后端源码、后端测试、数据库迁移：`D:\singuxplatform\nuwax-backend`。
- 不整目录覆盖 `D:\singuxplatform\x_frontend` 或其他历史副本。

## 今天的变更落点

| 项目 | 本地文件 | 状态 |
| --- | --- | --- |
| 模型代理路由 | `k8s/default.conf.template`、`Dockerfile`、`docker-compose.yml` | 保留已有专用 18086 路由 |
| 本地 Caddy 模型路由 | `deploy/caddy/Caddyfile.local` | 补齐专用 18086 路由，已生效 |
| 大文件入口限制 | `deploy/nginx/ciyuan.conf` | 保留 100m 设置 |
| 调试节点耗时和状态 | `src/pages/EditAgent/DebugDetails/NodeDetails/index.tsx`、语言文件 | 保留缺失耗时显示修复 |
| SSE 空帧 | 后端 `OpenAiApi.java`、`OpenAiApiStreamTest.java` | 保留过滤及测试 |
| 完整后端发布 | `deploy/backend-release.Dockerfile`、`deploy/backend-runtime.Dockerfile`、`deploy/deploy-backend-r2.sh` | r2 发布记录保留，构建文件增加 r3 测试 |
| 模型诊断脚本 | `scripts/test-model-api.py` | 本地文件，不包含密钥 |
| 工作流 URI | 后端 `ModelClientFactory.java`、`ModelEndpoint.java`、`ModelEndpointTest.java` | r3 源码 |
| 企业申请审核 | 前端 `tenantOnboarding.ts`、`TenantSelect/Onboarding.tsx`、`PlatformTenants/ApplicationReview.tsx`；后端 `TenantOnboardingService`、Mapper、实体、控制器与测试 | r3 源码，开关控制 |
| 新增表 | 后端 `sql/migrations/20260928-tenant-onboarding.sql` | 幂等新增表，不删除旧数据 |
| 说明 | `agent-model-runtime.md`、`enterprise-onboarding.md`、`multi-tenant-v2-plan.md`、根目录 `VERSION_CHANGES.md` | 已更新 |

这里的“本地同步”是保留并补齐源码及部署配置，不是从服务器反向覆盖整个仓库。服务器运行镜像、数据库或敏感配置不应直接覆盖本地开发资料。线上已发布 r2 与本地 r3 的验证、部署情况分别记录，不能混用版本结论。

## 本地运行结果

r3 后端镜像 `singux/backend:1.1.10-20260928-r3` 已构建并替换本地后端，状态 healthy。前端最终生产构建成功，由现有本地 Caddy 读取 `dist`；地址 `http://127.0.0.1:18090/login`。本地新增表迁移及 onboarding 开关已启用，重新登录后进入资料/企业选择流程。

健康接口 200；无凭据模型请求 403；未登录资料请求 4010。浏览器工具被客户端拦截，真实页面全链路未验收。生产服务器未在本轮升级。
