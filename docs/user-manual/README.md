# Singu X 智能体平台完整用户手册

更新日期：2026-10-04。基于当前项目源码与实施记录整理，适用于管理员、开发者和普通用户。

线上继续单租户。企业切换、全链路隔离、外部市场与企业支付不作为当前服务承诺。

包含项目操作指南及 85 篇关联文档的 Markdown 章节。原始 HTML 和素材单独保存在下载档案，不用于发布。截图包含旧品牌，整理版不嵌入截图。实际登录、权限和环境边界以项目操作指南为准，其余章节用于详细功能与接口参考。

## 推荐阅读

1. 阅读 [项目操作指南](project-guide.md)，确认登录和环境。
2. 普通用户阅读空间、问答智能体及常见问题。
3. 开发者阅读资源、工作流、通用智能体与网页开发。
4. 管理员阅读权限、系统配置、部署和批量导入。
5. 集成开发者阅读 API Key、会话、文件与开放 API。

## 完整目录

- [项目操作指南](project-guide.md)
- [完整合并版](../user-manual.md)

### 开始使用

- [平台概览](user-manual.md)
- [我的第一个智能体](first-agent.md)
- [通用型智能体指南](first-task-agent.md)
- [工作空间介绍](workspace.md)
- [常见问题（FAQ）](frequently-asked-questions.md)
- [常见术语](common-words.md)
- [常用词解释](%E5%B8%B8%E7%94%A8%E8%AF%8D%E8%A7%A3%E9%87%8A.md)

### 资源与智能体开发

- [智能体平台 · 插件系统介绍](plugin.md)
- [RAG知识库与知识图谱功能介绍](kb.md)
- [数据表功能介绍](table.md)
- [模型管理说明文档](model-management.md)
- [大模型接入](llm.md)
- [模型对外提供接口服务](model-relay-service.md)
- [MCP接入与开放](mcp.md)
- [工作流](workflow.md)
- [技能管理](skill-management.md)
- [子智能体](subagents.md)
- [智能体编排方式总览](agent-orchestration.md)
- [智能体编排](agent-design.md)
- [问答型智能体编排详解](qa-agent.md)
- [通用型智能体编排详解](general-agent.md)

### 应用、协作与运营

- [应用页面开发](page-develop.md)
- [IM 渠道对接文档](im-channel-integration.md)
- [任务中心](job.md)
- [日志查询](log-query.md)
- [共享资源与模板](ecosystem-market.md)
- [外部资源接入与管理](external-resources.md)
- [跨平台传递](xp.md)
- [对话框智能体](dialog-agent.md)

### 系统管理

- [平台系统模型管理](platform-model-config-price-monitor.md)
- [订阅与积分](platform-subscription-monetization.md)
- [支付与收益实施范围](platform-payment-revenue.md)
- [智能体平台 - 权限管理操作手册](permission-management.md)
- [智能体平台 - 沙盒配置操作手册](sandbox-management.md)
- [系统配置用户操作手册](system-config.md)

### 部署与客户端

- [平台安装、构建与增量更新](deploy.md)
- [智能体执行环境部署](agent-computer-deploy.md)
- [客户端与平台连接](docker-client-deploy.md)
- [Docker 多容器性能优化完整指南](docker-performance-optimization.md)

### 开放 API

- [获取API Key](api-key.md)
- [组件接入 - 独立会话页面](component-integration.md)
- [开始会话](conversation-chat.md)
- [创建会话](conversation-create.md)
- [访问会话文件](conversation-file-access.md)
- [查询会话文件列表](conversation-files.md)
- [查询智能体历史会话](conversation-list.md)
- [查询会话消息列表](conversation-messages.md)
- [查询会话信息](conversation-query.md)
- [停止会话](conversation-stop.md)
- [更新会话主题](conversation-update.md)
- [获取文件访问AK](open-api-file-ak.md)
- [文件上传](open-api-file-upload.md)
- [添加模型配置](open-api-model-add.md)
- [删除模型配置](open-api-model-delete.md)
- [查询模型配置详情](open-api-model-detail.md)
- [查询模型配置列表](open-api-model-list.md)
- [更新模型配置](open-api-model-update.md)
- [执行插件](open-api-plugin-execute.md)
- [创建团队空间](open-api-space-add.md)
- [删除团队空间](open-api-space-delete.md)
- [查询用户空间列表](open-api-space-list.md)
- [添加空间模型配置](open-api-space-model-add.md)
- [删除模型配置](open-api-space-model-delete.md)
- [查询模型配置详情](open-api-space-model-detail.md)
- [查询空间可使用模型列表](open-api-space-model-list.md)
- [更新空间模型配置](open-api-space-model-update.md)
- [更新团队空间](open-api-space-update.md)
- [根据ticket认证校验并跳转](open-api-ticket-redirect.md)
- [添加用户](open-api-user-add.md)
- [查询用户详细信息](open-api-user-detail.md)
- [禁用用户](open-api-user-disable.md)
- [启用用户](open-api-user-enable.md)
- [分页查询用户列表](open-api-user-list.md)
- [查询用户空间列表](open-api-user-space-list.md)
- [清除用户ticket认证](open-api-user-ticket-clear.md)
- [创建指定用户的认证ticket](open-api-user-ticket-create.md)
- [更新用户信息](open-api-user-update.md)
- [执行工作流](open-api-workflow-execute.md)
- [工作流流式执行](open-api-workflow-stream-execute.md)

### 案例与政策边界

- [高考填报志愿智能体](zhiyuan.md)
- [零代码生成客服智能体](kefu.md)
- [手机产品知识库示例（历史数据）](2025%E5%B9%B4%E4%B8%8A%E5%8D%8A%E5%B9%B4%E6%96%B0%E6%89%8B%E6%9C%BA%E4%BA%A7%E5%93%81%E7%9B%98%E7%82%B9.md)
- [用户服务协议编写要求](user-agreement.md)
- [开放使用与许可证边界](open-agreement.md)
- [隐私政策编写要求](privacy.md)

