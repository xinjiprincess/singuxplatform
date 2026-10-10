# 平台安装、构建与增量更新

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。

使用当前仓库的 Compose 和构建脚本，旧专用部署客户端不适用于定制项目。

## 环境准备

使用 package.json 约定的 Node.js、pnpm 及锁文件，容器构建需要 Docker 引擎与 Compose V2。配置数据库、缓存、模型代理、文件、调度及对象存储。

## 构建

当前前端仓库执行：

    pnpm install --frozen-lockfile
    pnpm build:prod

产物在 dist。开发使用 pnpm dev。本地镜像执行：

    .\deploy\build-local.ps1 -Components frontend,file-server

不自动替换运行容器。保留已有品牌及用户名登录修改，不能用其他副本覆盖。见 [本地构建](../local-docker-build.md)。

## 更新与回滚

按 [服务器增量更新](../server-incremental-update.md) 核对基线、移植最小补丁、备份、隔离验收，再更新验证过的镜像。线上单租户，不自动执行迁移或启用多企业。备份数据库、文件、配置与原镜像；失败恢复原制品，涉及数据结构时按迁移方案处理。
