# 访问会话文件

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/chat/{conversationId}/file/**`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`*/*`（二进制流）

**接口描述**:

静态文件访问，返回二进制流（图片、文件等），通过会话文件列表接口获取 `fileProxyUrl` 后使用

**请求示例**:

```
GET /api/v1/chat/1544687/file/html/index.html
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**路径参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| conversationId | 会话ID | 是 | integer(int64) |

**通配路径**:

`file/**` 后面的部分为文件的相对路径，通过 [查询会话文件列表](conversation-files.md) 接口返回的 `fileProxyUrl` 获取。

**响应参数**:

响应为文件的二进制流数据，Content-Type 根据文件类型自动设置。

**CURL示例**

```shell
# 下载文件到本地
curl 'http://127.0.0.1:8081/api/v1/chat/1544687/file/html/index.html' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  -o index.html
```

**TS模板示例**

```ts
/** 
 * 访问会话文件
 * @param {number} conversationId - 会话ID
 * @param {string} filePath - 文件相对路径
 * @returns
 */
export function getConversationFile(conversationId: number, filePath: string): Promise<Blob> {
  return request.get(`/api/v1/chat/${conversationId}/file/${filePath}`, {
    responseType: 'blob'
  });
}
```
