# 查询智能体历史会话

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/chat/conversation/list`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

查询指定智能体的历史会话列表，使用游标分页（通过 lastId 翻页）

**请求示例**:

```
GET /api/v1/chat/conversation/list?agentId=1596&limit=5
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**查询参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 | 默认值 |
| --- | --- | --- | --- | --- |
| agentId | 智能体ID | 是 | integer(int64) |  |
| lastId | 最后一条会话ID，用于翻页 | 否 | integer(int64) |  |
| limit | 返回数量限制 | 否 | integer(int32) | 10 |
| topic | 按会话主题模糊搜索 | 否 | string |  |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 会话列表 | array | ConversationDto |
|   id | 会话ID | integer(int64) |  |
|   tenantId | 租户ID | integer(int64) |  |
|   userId | 用户ID | integer(int64) |  |
|   uid | 会话UUID | string |  |
|   agentId | 智能体ID | integer(int64) |  |
|   topic | 会话主题 | string |  |
|   summary | 会话摘要 | string |  |
|   variables | 用户填写的会话变量内容 | object |  |
|   modified | 修改时间 | string(date-time) |  |
|   created | 创建时间 | string(date-time) |  |
|   agent | 智能体信息 | object | AgentDetailDto |
|   type | 会话类型，可用值: Chat, TempChat, TASK, TaskCenter | string |  |
|   taskId | 任务ID | string |  |
|   taskStatus | 任务状态，可用值: CREATE, EXECUTING, CANCEL, COMPLETE, FAILED | string |  |
|   taskCron | 定时任务表达式 | string |  |
|   taskCronDesc | 定时任务表达式描述 | string |  |
|   devMode | 开发模式 | integer(int32) |  |
|   topicUpdated | 主题是否更新 | integer(int32) |  |
|   sandboxServerId | 沙盒服务器ID | string |  |
|   sandboxSessionId | 沙盒会话ID | string |  |
|   sharedUris | 已分享的URI地址 | array |  |
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
				"type": "TaskAgent",
				"name": "TaskAgentTest",
				"hasPermission": false,
				"collect": false
			},
			"messageList": null,
			"type": "Chat",
			"taskId": null,
			"taskStatus": "CREATE",
			"taskCron": null,
			"taskCronDesc": "",
			"devMode": 0,
			"topicUpdated": 1,
			"sandboxServerId": null,
			"sandboxSessionId": null,
			"sharedUris": null
		}
	],
	"tid": "4361141776087082287",
	"success": true
}
```

**CURL示例**

```shell
# 查询前5条会话
curl 'http://127.0.0.1:8081/api/v1/chat/conversation/list?agentId=1596&limit=5' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

# 翻页查询
curl 'http://127.0.0.1:8081/api/v1/chat/conversation/list?agentId=1596&lastId=1545552&limit=5' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

# 按主题搜索
curl 'http://127.0.0.1:8081/api/v1/chat/conversation/list?agentId=1596&topic=Greeting' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 查询智能体历史会话（默认分页） | 0000 | 成功，返回最近10条会话 |
| 2 | 查询智能体历史会话（指定limit） | 0000 | 成功，返回指定数量的会话 |
| 3 | 翻页查询（传入lastId） | 0000 | 成功，返回lastId之后的会话 |
| 4 | 按主题搜索会话 | 0000 | 成功，返回匹配的会话列表 |

**TS模板示例**

```ts
// 会话信息（简化版）
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
  type?: 'Chat' | 'TempChat' | 'TASK' | 'TaskCenter';
  taskId?: string;
  taskStatus?: 'CREATE' | 'EXECUTING' | 'CANCEL' | 'COMPLETE' | 'FAILED';
  taskCron?: string;
  taskCronDesc?: string;
  devMode?: number;
  topicUpdated?: number;
  sandboxServerId?: string;
  sandboxSessionId?: string;
  sharedUris?: string[];
}

// 响应接口
export interface ConversationListRes {
  code: string;
  displayCode: string;
  message: string;
  data: ConversationDto[];
  tid: string;
  success: boolean;
}

/** 
 * 查询智能体历史会话
 * @param {number} agentId - 智能体ID
 * @param {number} lastId - 最后一条会话ID，用于翻页
 * @param {number} limit - 返回数量限制
 * @param {string} topic - 按会话主题搜索
 * @returns
 */
export function getConversationList(
  agentId: number,
  params?: { lastId?: number; limit?: number; topic?: string }
): Promise<ConversationListRes> {
  const query = new URLSearchParams();
  query.set('agentId', String(agentId));
  if (params?.lastId !== undefined) query.set('lastId', String(params.lastId));
  if (params?.limit !== undefined) query.set('limit', String(params.limit));
  if (params?.topic !== undefined) query.set('topic', params.topic);
  return request.get(`/api/v1/chat/conversation/list?${query}`);
}
```
