# 开始会话

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/chat/{conversationId}`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`text/event-stream`

**接口描述**:

智能体会话接口，响应为 Server-Sent Events (SSE) 流，返回数据为 JSON 格式

**请求示例**:

```javascript
{
  "conversationId": 1545551,
  "message": "你好",
  "attachments": [],
  "debug": false,
  "selectedComponents": []
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
| conversationId | 会话唯一标识 | 是 | integer(int64) |
| variableParams | 变量参数，前端需要根据agent配置组装参数 | 否 | object |
| message | chat消息 | 否 | string |
| attachments | 附件列表 | 否 | array |
|   fileKey |  | 否 | string |
|   fileUrl | 文件URL | 是 | string |
|   fileName |  | 否 | string |
|   mimeType | 文件类型 | 是 | string |
| debug | 是否调试模式 | 否 | boolean |
| sandboxId | 用户选择的沙盒（我的电脑）ID | 否 | integer(int64) |
| selectedComponents | 手动选择的组件列表 | 否 | array |
|   id | 组件ID | 否 | integer(int64) |
|   type | 组件类型，可用值: Plugin, Workflow, Trigger, Knowledge, Variable, Database, Model, Agent, Table, Mcp, Page, Event, Skill, SubAgent | 否 | string |
| skillIds | 前端选中的技能ID列表 | 否 | array |
| filterSensitive | 长期记忆中是否过滤敏感信息 | 否 | boolean |
| modelId | 用户选择的模型ID | 否 | integer(int64) |

## 响应参数

响应为 Server-Sent Events (SSE) 格式的文本流，每个事件包含 `AgentOutputDto` 结构的 JSON 数据。

| 参数名称 | 参数说明 | 类型 |
| --- | --- | --- |
| requestId | 请求唯一编号（任务编号） | string |
| eventType | 事件类型，可用值: PROCESSING, PROCESSING\_MESSAGE, MESSAGE, FINAL\_RESULT, HEART\_BEAT, ERROR | string |
| error | 会话出现异常时的错误信息 | string |
| data | 各个事件类型对应的数据 | object |
| completed | 输出过程中为false，最后一条消息会返回true | boolean |

## 事件说明

### PROCESSING

会话消息在输出过程中，智能体可能会调用不同的工具，`PROCESSING` 消息定义工具调用的开始和结束。

**data中的参数说明**:

| 参数名称 | 参数说明 | 类型 |
| --- | --- | --- |
| name | 工具名称 | string |
| icon | 工具图标 | string |
| type | 工具类型，包括Mcp、Plugin、Workflow、Table、Knowledge | string |
| status | 执行状态，包括 EXECUTING 执行中，FINISHED 执行完成 | string |
| result | 工具执行数据 | object |

### MESSAGE

| 参数名称 | 参数说明 | 类型 |
| --- | --- | --- |
| id | 消息ID | string |
| role | 可用值: USER, ASSISTANT | string |
| type | 可用值: CHAT 普通消息输出, THINK 思考消息, PROCESS\_OUTPUT 工作流过程输出, QUESTION 工作流问答节点 | string |
| text | 消息内容 | string |
| time | 消息时间 | string |
| attachments | 消息附件，一般用户消息才有 | array |
| think | 思考内容 | string |
| quotedText | 引用消息内容 | string |
| messageType | 可用值: USER, ASSISTANT | string |
| ext | 消息扩展内容 | array |
| finished | 是否消息内容输出结束 | boolean |

### HEARTBEAT

收到 HEARTBEAT 事件时可以直接忽略。

### FINAL\_RESULT

会话结束后的最终结果，包含 token 使用统计和汇总消息内容。

| 参数名称 | 参数说明 | 类型 |
| --- | --- | --- |
| success | 执行成功状态 | boolean |
| error | 执行失败信息 | string |
| startTime | 开始时间戳（毫秒） | number |
| endTime | 结束时间戳（毫秒） | number |
| completionTokens | 输出token数 | integer |
| promptTokens | 输入提示词token数 | integer |
| totalTokens | 总计token数 | integer |
| outputText | 汇总输出消息内容 | string |

**CURL示例**

```shell
curl -N 'http://127.0.0.1:8081/api/v1/chat/1545551' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{"conversationId": 1545551, "message": "你好"}'
```

**TS模板示例**

```ts
// 附件信息
export interface AttachmentDto {
  fileKey?: string;
  fileUrl: string;
  fileName?: string;
  mimeType: string;
}

// 手动选择的组件
export interface SelectedComponentDto {
  /* 组件ID */
  id: number;
  /* 组件类型 */
  type?: 'Plugin' | 'Workflow' | 'Trigger' | 'Knowledge' | 'Variable' | 'Database' | 'Model' | 'Agent' | 'Table' | 'Mcp' | 'Page' | 'Event' | 'Skill' | 'SubAgent';
}

// 请求参数
export interface TryReqDto {
  /* 会话唯一标识 */
  conversationId: number;
  /* 变量参数 */
  variableParams?: Record<string, unknown>;
  /* chat消息 */
  message?: string;
  /* 附件列表 */
  attachments?: AttachmentDto[];
  /* 是否调试模式 */
  debug?: boolean;
  /* 用户选择的沙盒ID */
  sandboxId?: number;
  /* 手动选择的组件列表 */
  selectedComponents?: SelectedComponentDto[];
  /* 前端选中的技能ID列表 */
  skillIds?: number[];
  /* 长期记忆中是否过滤敏感信息 */
  filterSensitive?: boolean;
  /* 用户选择的模型ID */
  modelId?: number;
}

// 响应事件
export interface AgentOutputDto {
  requestId?: string;
  eventType?: 'PROCESSING' | 'PROCESSING_MESSAGE' | 'MESSAGE' | 'FINAL_RESULT' | 'HEART_BEAT' | 'ERROR';
  error?: string;
  data?: unknown;
  completed?: boolean;
}

/** 
 * 开始会话（SSE流式响应）
 * @param {number} conversationId - 会话ID
 * @param {TryReqDto} params 
 * @returns
 */
export function startChat(conversationId: number, params: TryReqDto): Promise<void> {
  return request.post(`/api/v1/chat/${conversationId}`, params, {
    responseType: 'text',
    onDownloadProgress: (event) => {
      // 处理 SSE 事件流
    }
  });
}
```
