# 查询模型配置详情

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/model/{modelId}`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

查询指定模型配置的详细信息

**请求示例**:

```
GET /api/v1/model/100000006
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**路径参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| modelId | 模型ID | 是 | integer(int64) |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 模型配置详情 | object | ModelConfigDto |
|   id | 模型ID | integer(int64) |  |
|   tenantId | 租户ID | integer(int64) |  |
|   spaceId | 空间ID | integer(int64) |  |
|   creatorId | 创建者ID | integer(int64) |  |
|   scope | 模型生效范围，可用值: Space, Tenant, Global | string |  |
|   name | 模型名称 | string |  |
|   description | 模型描述 | string |  |
|   model | 模型标识 | string |  |
|   type | 模型类型，可用值: Completions, Chat, Multi, Edits, Images, Embeddings, Audio, Other | string |  |
|   isReasonModel | 是否为推理模型，0 否；1 是 | integer(int32) |  |
|   networkType | 网络类型，可用值: Internet, Intranet | string |  |
|   functionCall | 函数调用支持，可用值: Unsupported, CallSupported, StreamCallSupported | string |  |
|   maxTokens | 最大输出token数 | integer(int32) |  |
|   maxContextTokens | 上下文最大token数 | integer(int32) |  |
|   apiProtocol | 模型接口协议，可用值: OpenAI, Ollama, Zhipu, Anthropic | string |  |
|   apiInfoList | API列表 | array | ApiInfo |
|     url | 接口地址 | string |  |
|     key | 接口密钥 | string |  |
|     weight | 权重 | integer(int32) |  |
|   strategy | 接口调用策略，可用值: RoundRobin, WeightedRoundRobin, LeastConnections, WeightedLeastConnections, Random, ResponseTime | string |  |
|   dimension | 向量维度 | integer(int32) |  |
|   modified | 修改时间 | string(date-time) |  |
|   created | 创建时间 | string(date-time) |  |
|   creator | 创建者信息 | object | CreatorDto |
|     userId | 用户ID | integer(int64) |  |
|     userName | 用户名 | string |  |
|     nickName | 昵称 | string |  |
|     avatar | 头像 | string |  |
|   enabled | 是否启用，1-启用，0-禁用 | integer(int32) |  |
|   accessControl | 访问控制，0-不管控，1-管控 | integer(int32) |  |
|   usageScenarios | 可使用的业务场景，可用值: PageApp, TaskAgent, ChatBot, Workflow, OpenApi | array |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": {
		"id": 100000006,
		"tenantId": 1,
		"spaceId": 1071,
		"creatorId": 1,
		"scope": "Space",
		"name": "更新后的空间测试模型",
		"description": null,
		"model": "gpt-3.5-turbo-space",
		"type": "Chat",
		"isReasonModel": 0,
		"networkType": "Internet",
		"natInfoList": [],
		"functionCall": "CallSupported",
		"temperature": null,
		"topP": null,
		"maxTokens": 4096,
		"maxContextTokens": 128000,
		"apiProtocol": "OpenAI",
		"apiInfoList": [
			{
				"url": "https://api.openai.com/v1",
				"key": "sk-space-updated",
				"weight": 1
			}
		],
		"strategy": "WeightedRoundRobin",
		"dimension": 1536,
		"modified": "2026-04-13T12:34:24.000+00:00",
		"created": "2026-04-13T12:30:21.000+00:00",
		"creator": {
			"userId": 1,
			"userName": "fei",
			"nickName": "冯飞",
			"avatar": "https://agent-1251073634.cos.ap-chengdu.myqcloud.com/store/8698c0ff6c814ca3b477c4380b0efa5f.jpeg"
		},
		"enabled": 1,
		"accessControl": 0,
		"usageScenarios": ["Workflow", "TaskAgent", "PageApp", "ChatBot", "OpenApi"]
	},
	"tid": "4914111776083860316",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/model/100000006' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"success","data":{"id":100000006,"tenantId":1,"spaceId":1071,...},"tid":"4914111776083860316","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 查询存在的模型 | 0000 | 成功，返回模型完整配置信息 |
| 2 | 查询不存在的模型 | 4000 | 失败，提示"模型不存在" |

**TS模板示例**

```ts
// API信息
export interface ApiInfo {
  /* 接口地址 */
  url: string;
  /* 接口密钥 */
  key: string;
  /* 权重 */
  weight: number;
}

// 创建者信息
export interface CreatorDto {
  /* 用户ID */
  userId: number;
  /* 用户名 */
  userName: string;
  /* 昵称 */
  nickName: string;
  /* 头像 */
  avatar: string;
}

// 模型配置详情
export interface ModelConfigDto {
  /* 模型ID */
  id: number;
  /* 租户ID */
  tenantId: number;
  /* 空间ID */
  spaceId: number;
  /* 创建者ID */
  creatorId: number;
  /* 模型生效范围: Space, Tenant, Global */
  scope: 'Space' | 'Tenant' | 'Global';
  /* 模型名称 */
  name: string;
  /* 模型描述 */
  description: string | null;
  /* 模型标识 */
  model: string;
  /* 模型类型 */
  type: 'Completions' | 'Chat' | 'Multi' | 'Edits' | 'Images' | 'Embeddings' | 'Audio' | 'Other';
  /* 是否为推理模型 */
  isReasonModel: number;
  /* 网络类型: Internet, Intranet */
  networkType: 'Internet' | 'Intranet';
  /* 内网信息列表 */
  natInfoList: unknown[];
  /* 函数调用支持 */
  functionCall: 'Unsupported' | 'CallSupported' | 'StreamCallSupported';
  /* 温度参数 */
  temperature: unknown | null;
  /* topP参数 */
  topP: unknown | null;
  /* 最大输出token数 */
  maxTokens: number;
  /* 上下文最大token数 */
  maxContextTokens: number;
  /* 接口协议 */
  apiProtocol: 'OpenAI' | 'Ollama' | 'Zhipu' | 'Anthropic';
  /* API列表 */
  apiInfoList: ApiInfo[];
  /* 调用策略 */
  strategy: 'RoundRobin' | 'WeightedRoundRobin' | 'LeastConnections' | 'WeightedLeastConnections' | 'Random' | 'ResponseTime';
  /* 向量维度 */
  dimension: number;
  /* 修改时间 */
  modified: string;
  /* 创建时间 */
  created: string;
  /* 创建者信息 */
  creator: CreatorDto;
  /* 是否启用 */
  enabled: number;
  /* 访问控制 */
  accessControl: number;
  /* 使用场景 */
  usageScenarios: ('PageApp' | 'TaskAgent' | 'ChatBot' | 'Workflow' | 'OpenApi')[];
}

// 响应接口
export interface ModelDetailRes {
  code: string;
  displayCode: string;
  message: string;
  data: ModelConfigDto;
  tid: string;
  success: boolean;
}

/** 
 * 查询模型配置详情
 * @param {number} modelId - 模型ID
 * @returns
 */
export function getModelDetail(modelId: number): Promise<ModelDetailRes> {
  return request.get(`/api/v1/model/${modelId}`);
}
```
