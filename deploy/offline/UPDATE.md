# 用户列表导出与镜像更新

## 用户列表

用户管理页的“导出用户 CSV”导出最近一次成功查询的筛选结果，不限当前页，最多一万条。使用既有后端管理员/用户查询权限，不增加跨企业访问权限。不导出密码、令牌或密钥；CSV 带 UTF-8 BOM，可在 Excel 打开，已处理公式注入和引号换行。

这是分页读取，不是数据库事务快照。导出时避免同时修改用户；数量变化或重复 ID 会中止并提示重试。尚无独立的“导出”审计事件，现有后端查询日志不等于导出审计。完整多租户隔离仍未验收。

## 更新范围

`update.sh` 适用于此前 Linux 离线包的 `compose.json` + `.env` 部署，服务名称必须包含 frontend、backend、mysql。需要 Docker Compose（支持 `--wait`）、jq、sha256sum，及足够空间保存数据库备份和新旧镜像。

仅支持经发布者审核为数据库结构不变、数据向后兼容的镜像更新。修改表结构、配置项、依赖服务、数据格式或自动执行不兼容迁移的版本必须单独制定迁移和恢复流程，不能设置两个兼容标志来绕过审核。当前本机采用 dist/JAR 挂载，脚本会拒绝它，不会把运行时基础镜像误当最新代码。

更新前维护窗口内停止外部写入者。脚本停止本项目 frontend/backend，备份全部 MySQL 数据库、`.env` 和 Compose；只更新这两个应用服务，不升级 MySQL、Redis、MinIO 等，也不执行 SQL。外部任务、共享数据库写入者需要运营方另行停写。文件、对象存储和搜索数据不会自动备份；重要环境更新前仍应做全盘/数据卷快照。

## 离线更新

发布目录包含 `images.tar` 与 `update.json`，示例（摘要必须替换为实际值）：

```json
{
  "release": "版本号",
  "mode": "offline",
  "schemaUnchanged": true,
  "dataBackwardCompatible": true,
  "frontend": "sha256:前端镜像的64位ImageID",
  "backend": "sha256:后端镜像的64位ImageID",
  "archiveSha256": "images.tar的64位SHA256"
}
```

从可信渠道核对清单与摘要，然后执行：

```sh
sh update.sh /home/现有部署目录 /home/新版本目录
```

## 在线更新

同样使用可信 `update.json`，将 mode 设为 `online`，frontend/backend 指向自己发布仓库的 `仓库/镜像@sha256:64位摘要`，不使用 latest；不需要 images.tar。命令相同，脚本先拉取两个镜像，成功后才停服务。私有仓库先在服务器执行 docker login，不在清单里存密码。尚未建立或发布你的在线镜像仓库，当前没有可用的正式在线更新版本。

## 失败与恢复

使用 mkdir 锁防止并发更新；校验失败不停止应用。停机后异常会恢复旧镜像 ID，等待旧服务健康；数据库不自动恢复，以免覆盖新写入。回滚失败明确报错，需要人工介入。备份在原目录 `backups/时间-进程号`，权限受 umask 077 保护，含敏感配置，不要公开下载。

成功后 compose.json 保存新镜像引用，旧镜像和备份不自动删除。不要再运行旧包 deploy.sh：它用于初装且会再次导入旧 images.tar。重启用 `docker compose --env-file .env -f compose.json up -d --no-build --pull never`。

kill -9/断电不会触发回滚，会留下 `.update-lock`；先核对容器、备份及 compose.json，再人工处理锁。此脚本不是零停机升级、不是签名发布系统，也不是网页内升级按钮。

健康等待使用 [Docker Compose up 官方选项](https://docs.docker.com/reference/cli/docker/compose/up/)，仅健康检查成功不代表所有业务功能已验收。
