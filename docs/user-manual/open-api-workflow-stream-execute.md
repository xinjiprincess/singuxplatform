# 工作流流式执行

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/workflow/{id}/sse/execute`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`text/event-stream`

**接口描述**:

流式运行指定的工作流，请求体为动态参数，根据工作流定义的入参传递。响应为 Server-Sent Events (SSE) 流

**请求示例**:

```javascript
{
  "question": "用户输入的问题"
}
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**路径参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| id | 工作流ID | 是 | integer(int64) |

**请求体参数**:

动态参数，根据工作流定义的入参传递对应的 key-value 键值对。

**响应参数**:

响应为 Server-Sent Events (SSE) 格式的文本流，每个事件包含工作流执行的中间结果。

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/workflow/20/sse/execute' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{"question": "用户输入问题"}'
```

**测试用例**

| # | 场景 | 结果 |
| --- | --- | --- |
| 1 | 流式执行已发布的工作流 | 成功，返回 SSE 事件流 |
| 2 | 流式执行不存在或未发布的工作流 | 失败，返回错误响应 |

**TS模板示例**

```ts
/** 
 * 工作流流式执行
 * @param {number} id - 工作流ID
 * @param {Record<string, unknown>} params - 工作流动态入参
 * @returns
 */
export function streamExecuteWorkflow(id: number, params: Record<string, unknown>): Promise<void> {
  return request.post(`/api/v1/workflow/${id}/sse/execute`, params, {
    responseType: 'text',
    onDownloadProgress: (event) => {
      // 处理 SSE 事件流
      const chunk = event.currentTarget.response;
      // 解析 SSE 格式: data: {...}
    }
  });
}
```
