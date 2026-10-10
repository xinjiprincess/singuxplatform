# 根据ticket认证校验并跳转

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/ticket/redirect`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`无`（HTTP 重定向）

**接口描述**:

根据 ticket 进行认证校验，校验通过后直接跳转到指定的 redirectUrl。该接口为浏览器跳转使用，前端访问后会进行 302 重定向，并在响应头中 Set-Cookie 写入用户的登录凭证。

### 使用场景

当需要将智能体平台平台的页面（如会话页面、智能体页面等）嵌入到现有系统中时，可以通过该接口让用户快速登录，无需在嵌入页面中再次输入账号密码。

**接入流程**：

1.  接入系统通过 API 获取用户的 ticket（调用 [创建认证ticket](open-api-user-ticket-create.md) 接口）
2.  使用 ticket 认证跳转到目标页面（调用本接口）

**请求示例**:

```
GET /api/ticket/redirect?ticket=2c1259ec995c4b0092eabdec2e4d5400&redirectUrl=https://example.com
```

## 请求参数

**查询参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| ticket | 认证ticket | 是 | string |
| redirectUrl | 认证成功后跳转的目标URL | 是 | string |

**响应说明**:

认证成功后返回 HTTP 302 重定向到目标 URL，认证失败返回 403 Forbidden。

**CURL示例**

```shell
# 注意：curl 默认会跟随重定向，使用 -v 可查看重定向过程
curl -v 'http://127.0.0.1:8081/api/ticket/redirect?ticket=2c1259ec995c4b0092eabdec2e4d5400&redirectUrl=https://example.com'

# 不跟随重定向，仅查看 302 响应
curl -L0 'http://127.0.0.1:8081/api/ticket/redirect?ticket=2c1259ec995c4b0092eabdec2e4d5400&redirectUrl=https://example.com'
```

**TS模板示例**

```ts
/** 
 * 根据ticket认证校验并跳转
 * 注意：此接口为浏览器跳转使用，前端通常通过 window.location.href 调用
 * @param {string} ticket - 认证ticket
 * @param {string} redirectUrl - 认证成功后跳转的目标URL
 */
export function ticketRedirect(ticket: string, redirectUrl: string): void {
  window.location.href = `/api/ticket/redirect?ticket=${encodeURIComponent(ticket)}&redirectUrl=${encodeURIComponent(redirectUrl)}`;
}
```
