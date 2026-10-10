# 更新会话主题

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/chat/conversation/{conversationId}/update`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`*/*`

**接口描述**:

更新指定会话的主题名称，可通过 `firstMessage` 或 `topic` 设置，二者至少提供一个

**请求示例**:

```javascript
{
  "firstMessage": "你好，请问今天天气怎么样？"
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
| conversationId | 会话ID | 是 | integer(int64) |

**请求体参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| firstMessage | 用户第一条消息 | 是 | string |
| topic | 会话主题，可以不传，firstMessage与topic二选一 | 否 | string |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 更新后的会话信息 | object | ConversationDto |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": {
		"id": 1545552,
		"tenantId": 1,
		"userId": 1,
		"uid": "3787cf89001f43bd832b7adeb8134d96",
		"agentId": 1596,
		"topic": "自定义会话主题",
		"summary": null,
		"variables": null,
		"modified": "2026-04-13T13:07:54.000+00:00",
		"created": "2026-04-13T13:07:10.000+00:00",
		"agent": {
			"agentId": 1596,
			"name": "TaskAgentTest",
			"type": "TaskAgent",
			"icon": "https://testagent.xspaceagi.com/api/logo/agent/TaskAgentTest",
			"publishDate": "2026-04-05T16:35:39.000+00:00"
		},
		"messageList": null,
		"type": "Chat",
		"taskId": null,
		"taskStatus": "CREATE",
		"devMode": 0,
		"topicUpdated": 1
	},
	"tid": "2798491776085673993",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/chat/conversation/1545552/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{"firstMessage": "你好，请问今天天气怎么样？"}'

{"code":"0000","displayCode":"0000","message":"success","data":{"id":1545552,...},"tid":"5761521776085637682","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 使用 firstMessage 更新主题 | 0000 | 成功，主题更新为第一条消息内容 |
| 2 | 使用 topic 更新主题 | 0000 | 成功，主题更新为自定义内容 |

**TS模板示例**

```ts
// 请求参数
export interface ConversationUpdateDto {
  /* 用户第一条消息 */
  firstMessage: string;
  /* 会话主题，可以不传，firstMessage与topic二选一 */
  topic?: string;
}

// 会话信息
export interface ConversationDto {
  id: number;
  tenantId?: number;
  userId?: number;
  uid?: string;
  agentId?: number;
  topic?: string;
  summary?: string;
  variables?: Record<string, unknown>;
  modified?: string;
  created?: string;
  agent?: unknown;
  messageList?: unknown[];
  type?: string;
  taskId?: string;
  taskStatus?: string;
  taskCron?: string;
  taskCronDesc?: string;
  devMode?: number;
  topicUpdated?: number;
  sandboxServerId?: string;
  sandboxSessionId?: string;
  sharedUris?: string[];
}

// 响应接口
export interface ConversationUpdateRes {
  code: string;
  displayCode: string;
  message: string;
  data: ConversationDto;
  tid: string;
  success: boolean;
}

/** 
 * 更新会话主题
 * @param {number} conversationId - 会话ID
 * @param {ConversationUpdateDto} params 
 * @returns
 */
export function updateConversation(conversationId: number, params: ConversationUpdateDto): Promise<ConversationUpdateRes> {
  return request.post(`/api/v1/chat/conversation/${conversationId}/update`, params);
}
```
