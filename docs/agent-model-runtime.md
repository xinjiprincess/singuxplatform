# Singu X 智能体与模型运行设计

更新：2026-09-28。本文根据本地源码说明当前实现，不代表所有能力已部署或完成隔离验收。

## 代码位置与边界

- 前端：`C:\Users\zhang\nuwax`。
- 后端：`D:\singuxplatform\nuwax-backend`。
- 智能体编排：`app-platform-modules/app-platform-agent`。
- 模型代理：`app-platform-modules/app-platform-model-proxy`。
- 账号、租户、成员关系：`app-platform-modules/platform-system`。
- HTTP 登录拦截：`app-platform-bootstrap/app-platform-web-bootstrap` 下的 `AuthInterceptor`。

## 一次模型调用

1. 浏览器提交会话或工作流试运行请求。后端验证账号及租户会话，构造请求、智能体、工作流上下文。
2. 智能体负责组合提示词、历史消息、附件及可调用组件，不等同于大模型本身。
3. 工作流的 `LLMNodeHandler` 从节点配置取得模型及提示词，将工作流上下文复制为 `AgentContext`，组装 `ModelContext` 后调用 `ModelInvoker`。
4. `ModelInvoker` 准备消息、运行参数、工具回调及 TraceContext，使用 `ModelClientFactory` 创建 Spring AI ChatClient。
5. 工厂通过 `WeightedRoundRobinStrategy` 按权重选取模型配置中的 API 地址，并根据 OpenAI、Anthropic、Ollama 协议建立适配器。向量模型走独立 embedding 路径。
6. 文本模型不是简单地由浏览器直连供应商：后端先调用 `ModelApiProxyRpcService` 生成代理凭证，代理配置携带上游地址、密钥、模型名称及追踪信息。
7. 后端通过模型代理调用上游；代理凭证仍需校验。业务接口和模型代理使用不同端口，不能把模型请求转发至普通登录业务接口。
8. 流式结果转换为 `CallMessage`，包含正文、推理、工具执行等事件。工作流节点汇总结果，智能体对话则把事件推送到前端。

## 工具与工作流

`ModelInvoker` 支持注册 ToolCallback，并根据模型能力使用原生工具调用或提示词驱动的工具解析。工具结果可进入后续模型调用。工作流则按配置的节点及变量引用运行，维护节点输入、输出、状态与循环上下文。

模型输出不能代替权限判断：任何工具读取资源、上传文件或触发工作流时，都必须保持原请求的用户与租户权限。跨线程任务不能仅依赖线程局部变量中的租户 ID。

## 流式响应与空输出

- 空 SSE 数据帧不是 JSON 文档；现有 `OpenAiApi` 修复会跳过空帧。
- HTTP 200 不必然代表模型生成成功。网关也可能返回业务错误 JSON；代理路由错误时尤其如此。
- Token 数量与正文是不同字段。存在 usage 或 reasoning 并不证明有最终正文；工具调用也可能没有普通正文。
- 排查时同时核对 requestId、响应类型、正文/推理/工具调用、finish reason、节点结束时间，不能只看“成功”标签。
- `ModelInvoker` 从响应 usage 记录用量，部分路径使用本地 Token 估算。不能把估算值作为已实现的企业计费结算。

## URI 错误与本次修复

旧的 `ModelClientFactory` 从 `AgentContext.tenantConfig.siteUrl` 推导代理地址。上下文没有站点信息时，可能得到 `/api/proxy/model`，Java HTTP 客户端因此报 `URI with undefined scheme`。

本次将后端内部调用地址独立为 `model-api-proxy.internal-base-url`，缺省是 `http://127.0.0.1:${model-api-proxy.port:18086}`。后端和模型代理在同一进程部署时使用这个缺省值；将代理拆为单独服务后必须配置其可达地址。

此设置仅用于后端模型工厂，不把 localhost 地址返回给桌面端或外部客户端。仍然申请并携带代理凭证，不绕过代理授权与追踪。

上游 URL 必须显式填写协议，例如 `http://61.188.36.255:18000/mass/v1`，而不是 `61.188.36.255:18000/mass/v1`。新增校验拒绝相对地址、URL 内嵌凭证、查询串和片段，错误消息不回显密钥。HTTP 会明文传输凭证；供应商支持 HTTPS 时应使用 HTTPS。

## 多企业会话

开启现有多企业开关后，账号先获取短期身份票据，再选择有效成员关系中的企业，签发绑定 tenantId 与成员版本的会话。切换企业重新签发令牌并清理前端租户缓存。

新增首次登录资料和企业申请不授予业务权限。申请通过后才建立 OWNER（创建企业）或 MEMBER（加入企业）成员关系。平台管理员权限与普通企业管理员权限分开校验。

## 现存边界

- 完整数据隔离需要逐项验收 SQL、文件、Redis、向量库、搜索索引、分享、异步任务和工具，不能仅凭 JWT 中存在 tenantId 宣称完成。
- Caddy 是企业自定义域名的选定方案；已有线上主站此前使用 Nginx/Certbot。新建租户不自动创建 DNS 或证书。
- 免费套餐禁自定义品牌/域名；额度配置与真正原子扣减需要分开确认。微信、支付宝目前仍为预留接口，不收款。
- 本文不包含密码、API Key、票据或服务器私密配置。

## 诊断脚本

`scripts/test-model-api.py` 可分别测试非流式和 SSE。使用环境变量 `MODEL_API_KEY` 或脚本的隐藏输入；不要将密钥写入脚本。`--probe` 仅测试未认证连通性，不能证明模型可用。`--no-proxy` 用于排除本机系统代理影响。
