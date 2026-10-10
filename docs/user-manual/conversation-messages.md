# 查询会话消息列表

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/chat/{conversationId}/messages`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

查询指定会话中的消息列表，支持分页查询

**请求示例**:

```
GET /api/v1/chat/1545556/messages?index=174590&limit=10
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

**查询参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 | 默认值 |
| --- | --- | --- | --- | --- |
| index | 消息索引起始位置 | 否 | integer(int64) |  |
| limit | 返回消息数量限制 | 否 | integer(int32) | 10 |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 消息列表 | array | ChatMessageDto |
|   index | 消息索引 | integer(int64) |  |
|   tenantId | 租户ID | integer(int64) |  |
|   senderType | 消息发送方类型，可用值: USER, AGENT | string |  |
|   senderId | 消息发送方ID | string |  |
|   userId | 关联用户ID | integer(int64) |  |
|   agentId | 关联的智能体ID | integer(int64) |  |
|   id | 消息ID | string |  |
|   role | 消息角色，可用值: USER, ASSISTANT, SYSTEM, FUNCTION | string |  |
|   type | 消息类型，可用值: CHAT, THINK, PROCESS\_OUTPUT, QUESTION, ANSWER | string |  |
|   text | 消息内容 | string |  |
|   time | 消息时间 | string(date-time) |  |
|   attachments | 消息附件 | array | AttachmentDto |
|     fileKey |  | string |  |
|     fileUrl | 文件URL | string |  |
|     fileName |  | string |  |
|     mimeType | 文件类型 | string |  |
|   think | 思考内容 | string |  |
|   quotedText | 引用消息内容 | string |  |
|   finished | 是否消息内容输出结束 | boolean |  |
|   finishReason | 完成原因 | string |  |
|   componentExecutedList | 执行过程输出数据 | array |  |
|   metadata | 消息扩展内容 | object |  |
|   messageType | 消息类型，可用值: USER, ASSISTANT, SYSTEM, TOOL | string |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": [
		{
			"index": 174590,
			"tenantId": 1,
			"senderType": "USER",
			"senderId": "1",
			"userId": 1,
			"agentId": 1596,
			"id": "d5be409c98f44928bcb1cd5a935912cf",
			"role": "USER",
			"type": "CHAT",
			"text": "帮我做一个简单的天气卡片网页，包含温度、天气图标和位置信息",
			"time": "2026-04-13T13:19:09.000+00:00",
			"attachments": null,
			"think": null,
			"quotedText": null,
			"finished": false,
			"finishReason": null,
			"componentExecutedList": null,
			"metadata": null,
			"messageType": "USER"
		},
		{
			"index": 174591,
			"tenantId": 1,
			"senderType": "AGENT",
			"senderId": "1596",
			"userId": 1,
			"agentId": 1596,
			"id": "abc123",
			"role": "ASSISTANT",
			"type": "CHAT",
			"text": "你好！我是一个天气卡片...",
			"time": "2026-04-13T13:19:15.000+00:00",
			"attachments": null,
			"think": null,
			"quotedText": null,
			"finished": true,
			"finishReason": "ENDTURN",
			"componentExecutedList": [],
			"metadata": null,
			"messageType": "ASSISTANT"
		}
	],
	"tid": "6044751776086475149",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/chat/1545556/messages?index=174590&limit=10' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"success","data":[...],"tid":"6044751776086475149","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 查询会话消息（默认分页） | 0000 | 成功，返回最近10条消息 |
| 2 | 查询会话消息（指定起始索引） | 0000 | 成功，从指定索引开始返回 |

**TS模板示例**

```ts
// 附件信息
export interface AttachmentDto {
  fileKey?: string;
  fileUrl: string;
  fileName?: string;
  mimeType: string;
}

// 会话消息
export interface ChatMessageDto {
  index?: number;
  tenantId?: number;
  senderType?: 'USER' | 'AGENT';
  senderId?: string;
  userId?: number;
  agentId?: number;
  id: string;
  role: 'USER' | 'ASSISTANT' | 'SYSTEM' | 'FUNCTION';
  type?: 'CHAT' | 'THINK' | 'PROCESS_OUTPUT' | 'QUESTION' | 'ANSWER';
  text?: string;
  time?: string;
  attachments?: AttachmentDto[];
  think?: string;
  quotedText?: string;
  finished?: boolean;
  finishReason?: string;
  componentExecutedList?: unknown[];
  metadata?: Record<string, unknown>;
  messageType?: 'USER' | 'ASSISTANT' | 'SYSTEM' | 'TOOL';
}

// 响应接口
export interface ConversationMessagesRes {
  code: string;
  displayCode: string;
  message: string;
  data: ChatMessageDto[];
  tid: string;
  success: boolean;
}

/** 
 * 查询会话消息列表
 * @param {number} conversationId - 会话ID
 * @param {number} index - 消息索引起始位置
 * @param {number} limit - 返回消息数量限制
 * @returns
 */
export function getConversationMessages(
  conversationId: number,
  index?: number,
  limit?: number
): Promise<ConversationMessagesRes> {
  const params = new URLSearchParams();
  if (index !== undefined) params.set('index', String(index));
  if (limit !== undefined) params.set('limit', String(limit));
  const query = params.toString() ? `?${params}` : '';
  return request.get(`/api/v1/chat/${conversationId}/messages${query}`);
}
```
