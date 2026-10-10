# 知识库单租户修复包

只适用于已核验的线上 `singux/backend:1.1.10-20260928-r2` 基线。归档 SHA256 为 `dcb6cb2a4c0bda989c67bf1e4f6cc9593f988ac71054adf9391a8a909e5bbe8a`。补丁不改变登录、账号、前端、租户配置和数据库结构，不重设管理员密码；不启用比赛入口。

## 范围和限制

- 修复 Elasticsearch 9.x 客户端与线上 8.18.0 不兼容，以及查询/删除隐式创建全文索引的问题。
- 基于生产 JAR 编译，仅替换 `ElasticsearchServiceImpl.class`、两项 Elasticsearch 库及两项 HTTP 运行依赖，同步 Spring Boot 索引。其余业务条目保持原样。
- 保留生产知识库领域类原样，因此不包含多租户开发版的删除顺序调整。没有索引时可删除，不代表新建全文索引无需 IK；索引写入仍需要单独安装对应版本的 IK 插件。
- Docker 独立 Elasticsearch 测试覆盖空索引、指定知识库删除、其他知识库/租户保留和重复删除。尚未验证完整生产 HTTP/MySQL/Milvus 删除链路，也未对生产备份做恢复演练。
- 更新器的失败路径通过模拟测试，不代表已经在生产完成升级或恢复。首次执行前应有云磁盘快照或独立离机备份，并先在副本环境做恢复验证。

## 传输与只读检查

在本机 PowerShell 上传压缩包和校验文件，仍使用已验证 SSH 主机记录：

```powershell
scp -o "UserKnownHostsFile=C:/Users/zhang/nuwax/tmp/server-knowledge-known-hosts" -o "StrictHostKeyChecking=yes" C:/Users/zhang/nuwax/outputs/singux-knowledge-singletenant-20261007.tar.gz C:/Users/zhang/nuwax/outputs/singux-knowledge-singletenant-20261007.tar.gz.sha256 root@43.136.175.19:/data/singux-update/
```

服务器执行：

```sh
cd /data/singux-update
sha256sum -c singux-knowledge-singletenant-20261007.tar.gz.sha256
tar -xzf singux-knowledge-singletenant-20261007.tar.gz
cd singux-knowledge-singletenant-20261007
sha256sum -c SHA256SUMS
python3 update-knowledge.py /home/singu-x-1.1.10-20260924-r1-linux-amd64 "$PWD"
```

默认检查不停止或更新服务。它核对实际项目、目录、运行 JAR、数据挂载、原服务健康、补丁校验及 `/data` 空间。检查通过后显示 `CHECK_OK`。发现未知可写 bind mount、应用覆盖挂载、基线不同或空间不足会拒绝更新。只读检查会启动临时只读容器统计卷大小，不写入卷。

## 维护窗口更新

只有只读检查通过、恢复验证完成且已暂停导入/外部写入后才能执行：

```sh
python3 update-knowledge.py /home/singu-x-1.1.10-20260924-r1-linux-amd64 "$PWD" --apply
```

此操作会临时停止整个 `singux` 项目：先停止后端并导出 MySQL，再停止项目内所有正在运行的服务，逐卷进行冷备份，包括匿名卷。停机时间由数据量决定，可能较长；另一个 Compose 项目的下载站不在此脚本管理范围内。必须确认它或其他外部服务不会写同一份数据。

备份保存在 `/data/singux-backups/knowledge-时间-进程号`，包含 SQL、数据卷归档、配置、原运行镜像、校验和及 `BACKUP_COMPLETE`。归档可读与校验通过不等于完整恢复成功。备份含账号及文件等敏感数据，应限制访问，并复制到服务器之外。服务器端通过原镜像和补丁 JAR 构建新镜像，不重新下载全部基础镜像。

更新只修改原 Compose 中 backend 的镜像，保留项目名、环境变量、端口和卷。原基础设施恢复原镜像运行；前端仅重启以刷新 Nginx 后端地址。健康失败会尝试恢复原镜像与配置，不自动覆盖数据库或文件。被强制断电或 `kill -9` 时无法保证自动回退，需人工介入；锁目录不能在另一次更新仍运行时删除。

## 验收和回退

出现 `UPDATE_OK` 后还需检查域名登录、原账号、模型调用、上传下载、知识库检索及删除（仅对可丢弃测试库操作），然后恢复用户写入。检查备案底部和原官网路由仍保持不变。

业务异常时可手动恢复旧镜像：将下面 `BACKUP` 换成更新器输出的完整备份目录。此命令不会恢复旧数据库，不会覆盖更新后新增的数据。

```sh
cd /home/singu-x-1.1.10-20260924-r1-linux-amd64
BACKUP=/data/singux-backups/knowledge-实际备份目录
test -s "$BACKUP/rollback-compose.json" || exit 1
cp "$BACKUP/rollback-compose.json" compose.json
docker compose -p singux --env-file .env -f compose.json up -d --no-deps --no-build --pull never --wait --wait-timeout 600 backend frontend
docker compose -p singux --env-file .env -f compose.json restart frontend
docker compose -p singux --env-file .env -f compose.json ps
```

不要运行 `down -v`、卷清理、初装部署脚本或租户迁移 SQL。数据损坏时应先保全最新状态，按单独验证过的恢复流程处理；不要在线解压数据卷归档覆盖正在运行的数据库。
