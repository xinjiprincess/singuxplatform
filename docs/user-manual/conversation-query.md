# 查询会话信息

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/chat/conversation/{id}`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

查询指定会话的详细信息，包含会话中的历史消息

**请求示例**:

```
GET /api/v1/chat/conversation/1545551
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**路径参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| id | 会话ID | 是 | integer(int64) |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 会话信息 | object | ConversationDto |
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
|   messageList | 会话消息列表 | array | ChatMessageDto |
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
	"data": {
		"id": 1545551,
		"tenantId": 1,
		"userId": 1,
		"uid": "c1e2c0c32a844127a829560641b9da57",
		"agentId": 1596,
		"topic": "和TaskAgentTest开始会话",
		"summary": null,
		"variables": null,
		"modified": "2026-04-13T13:02:25.000+00:00",
		"created": "2026-04-13T13:02:25.000+00:00",
		"agent": {
			"spaceId": 57,
			"creatorId": 1,
			"agentId": 1596,
			"uid": "255233c81c144196819426878d7449bf",
			"type": "TaskAgent",
			"name": "TaskAgentTest",
			"description": null,
			"icon": "https://testagent.xspaceagi.com/api/logo/agent/TaskAgentTest",
			"remark": null,
			"publishDate": "2026-04-05T16:35:39.000+00:00",
			"statistics": {
				"targetId": 1596,
				"userCount": 17,
				"convCount": 964,
				"collectCount": 2,
				"likeCount": 0
			},
			"publishUser": {
				"userId": 1,
				"userName": "fei",
				"nickName": "冯飞",
				"avatar": "https://agent-1251073634.cos.ap-chengdu.myqcloud.com/store/8698c0ff6c814ca3b477c4380b0efa5f.jpeg"
			},
			"category": "BusinessService",
			"openSuggest": "Close",
			"shareLink": "https://testagent.xspaceagi.com/agent/1596",
			"manualComponents": [],
			"allowCopy": 1,
			"hasPermission": true,
			"allowOtherModel": 1,
			"allowAtSkill": 1,
			"allowPrivateSandbox": 1,
			"collect": false
		},
		"messageList": null,
		"type": "Chat",
		"taskId": null,
		"taskStatus": "CREATE",
		"taskCronDesc": "",
		"devMode": 0,
		"topicUpdated": 0,
		"sandboxServerId": null,
		"sandboxSessionId": null,
		"sharedUris": null
	},
	"tid": "8681381776085355631",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/chat/conversation/1545551' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"success","data":{"id":1545551,...},"tid":"8681381776085355631","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 查询存在的会话 | 0000 | 成功，返回会话详细信息（含智能体信息） |

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

// 统计信息
export interface StatisticsDto {
  targetId?: number;
  userCount?: number;
  convCount?: number;
  collectCount?: number;
  likeCount?: number;
  referenceCount?: number;
  callCount?: number;
  failCallCount?: number;
  totalCallDuration?: number;
}

// 发布者信息
export interface PublishUserDto {
  userId: number;
  userName: string;
  nickName: string;
  avatar: string;
}

// 智能体信息
export interface AgentDetailDto {
  spaceId?: number;
  creatorId?: number;
  agentId?: number;
  uid?: string;
  type?: string;
  name?: string;
  description?: string;
  icon?: string;
  remark?: string;
  publishDate?: string;
  statistics?: StatisticsDto;
  publishUser?: PublishUserDto;
  category?: string;
  openSuggest?: 'Open' | 'Close';
  openingChatMsg?: string;
  openingGuidQuestions?: string[];
  guidQuestionDtos?: unknown[];
  openScheduledTask?: 'Open' | 'Close';
  variables?: unknown[];
  shareLink?: string;
  manualComponents?: unknown[];
  allowCopy?: number;
  conversationId?: number;
  sandboxId?: number;
  hasPermission?: boolean;
  expandPageArea?: number;
  hideChatArea?: number;
  hideDesktop?: number;
  allowOtherModel?: number;
  allowAtSkill?: number;
  allowPrivateSandbox?: number;
  pageHomeIndex?: string;
  eventBindConfig?: unknown;
  collect?: boolean;
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
  agent?: AgentDetailDto;
  messageList?: ChatMessageDto[];
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
export interface ConversationQueryRes {
  code: string;
  displayCode: string;
  message: string;
  data: ConversationDto;
  tid: string;
  success: boolean;
}

/** 
 * 查询会话信息
 * @param {number} id - 会话ID
 * @returns
 */
export function getConversation(id: number): Promise<ConversationQueryRes> {
  return request.get(`/api/v1/chat/conversation/${id}`);
}
```
