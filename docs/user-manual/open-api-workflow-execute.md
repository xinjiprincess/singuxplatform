# 执行工作流

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/workflow/{id}/execute`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`*/*`

**接口描述**:

运行指定的工作流，请求体为动态参数，根据工作流定义的入参传递

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

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 工作流执行返回的结果 | object |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": {},
	"tid": "1234567890123456789",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/workflow/20/execute' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{"question": "用户输入问题"}'

{"code":"0000","displayCode":"0000","message":"success","data":{},"tid":"1234567890123456789","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 执行已发布的工作流 | 0000 | 成功，返回工作流执行结果 |
| 2 | 执行不存在或未发布的工作流 | 0001 | 失败，提示"Error workflow id or not published" |

**TS模板示例**

```ts
// 响应接口
export interface WorkflowExecuteRes {
  code: string;
  displayCode: string;
  message: string;
  data: object | null;
  tid: string;
  success: boolean;
}

/** 
 * 执行工作流
 * @param {number} id - 工作流ID
 * @param {Record<string, unknown>} params - 工作流动态入参
 * @returns
 */
export function executeWorkflow(id: number, params: Record<string, unknown>): Promise<WorkflowExecuteRes> {
  return request.post(`/api/v1/workflow/${id}/execute`, params);
}
```
