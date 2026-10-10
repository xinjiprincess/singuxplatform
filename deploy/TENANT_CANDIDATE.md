# Singu X 多企业管理候选包（2026-10-08）

此包用于上传保存、独立环境验证，不是已经完成生产迁移演练的更新包。

## 包含内容

- Linux amd64 镜像：后端 `singux/backend:1.1.10-20261008-tenant-admin-r2`、前端 `singux/frontend:1.1.10-20261008-tenant-admin`。
- 根平台新增企业、企业选择搜索、网页用户批量添加/禁用/启用、企业成员批量移出/恢复。
- 当前本地工作区既有的多企业、比赛入口、品牌与其他修复；不是只包含本轮变化的单租户补丁。
- 校验值、增量数据库迁移源码及本地验收脚本。没有生产配置、数据备份、密码、API Key、用户名单或本地种子 SQL。
- 新批量接口使用数据库自增用户 ID 和随机默认 UID，调用方也可指定 UID；不更改历史账号 ID/UID。旧单用户新增接口的时间桶 ID 算法不在此补丁修复范围。

## 上传后先做什么

本机 PowerShell 上传（使用此前已核对指纹的专用 known_hosts）：

```powershell
scp -o "UserKnownHostsFile=C:/Users/zhang/nuwax/tmp/server-knowledge-known-hosts" -o "StrictHostKeyChecking=yes" C:/Users/zhang/nuwax/outputs/singux-tenant-admin-20261008-candidate-r2.tar.gz C:/Users/zhang/nuwax/outputs/singux-tenant-admin-20261008-candidate-r2.tar.gz.sha256 root@43.136.175.19:/data/singux-update/
```

服务器上只校验与导入，尚不切换服务：

```bash
cd /data/singux-update
sha256sum -c singux-tenant-admin-20261008-candidate-r2.tar.gz.sha256
tar -xzf singux-tenant-admin-20261008-candidate-r2.tar.gz
cd singux-tenant-admin-20261008-candidate-r2
sha256sum -c SHA256SUMS
docker load -i images.tar
```

1. 在服务器验证外层压缩包 SHA256，再解压并运行 `sha256sum -c SHA256SUMS`。
2. `docker load -i images.tar` 只导入镜像，不会切换现有容器，也不修改用户/数据库。
3. 不要立即在原项目执行 `docker compose up`，也不要覆盖原 `.env`、`compose.json`。
4. 独立 Compose 项目、网络和卷恢复生产备份，保留原用户 ID、租户 ID、空间和知识库归属。迁移文件需按实际数据库版本审核，不能对照本地种子重建数据库。
5. 开多企业之前核对全局登录标识冲突、每个企业有效所有者、平台管理员授权 ID、业务资源/搜索/向量/文件/SSE/沙箱/API Key 的隔离。移出企业须使旧会话失效。
6. 旧生产版的 `update-knowledge.py` 只适用于知识库单租户热修复，不适用于本包。

## 主要配置

`PLATFORM_TENANT_POLICY_ENABLED=true`、`PLATFORM_MEMBERSHIP_ENABLED=true` 在表结构及成员回填完成后才启用；`PLATFORM_ADMIN_USER_IDS` 必须填写实际平台超管用户 ID。`PLATFORM_ROOT_TENANT_ID` 默认 1，需与生产根企业一致。不要更改现有管理员密码。

`PLATFORM_ONBOARDING_ENABLED`、`PLATFORM_PORTALS_ENABLED` 与其他已有选项需按审核范围启用；不能把本机整份配置覆盖到服务器。新增开放 API 权限项需核对旧管理员 Key 的显式授权范围，管理员身份不代表自动具有新增接口权限。

## 切换与恢复边界

维护窗口停止写入，备份 SQL、全部卷和配置并离机保存；固定原 Compose 项目 `singux` 及现有数据卷，只替换应用服务。先验证原用户登录、模型调用、文件读写、知识库以及多企业越权路径，再放开新企业。

严禁 `docker compose down -v`、卷删除或用本地数据库覆盖生产。多企业新写入产生后，不能直接换回旧无隔离的单租户镜像；回滚需要维护窗口和兼容新数据模型的方案，不自动恢复旧备份覆盖新增数据。

仍待完成：生产备份恢复与迁移演练、全业务隔离验收、生产切换脚本。当前没有宣称这些已经通过。
