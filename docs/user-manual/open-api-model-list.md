# 查询模型配置列表

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/model/list`

**请求方式**:`GET`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

查询全部模型配置列表

**请求示例**:

```
GET /api/v1/system/model/list
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 模型配置列表 | array | ModelConfigDto |
|   id | 模型ID | integer(int64) |  |
|   tenantId | 商户ID | integer(int64) |  |
|   spaceId | 空间ID | integer(int64) |  |
|   scope | 模型生效范围，可用值: Space, Tenant, Global | string |  |
|   name | 模型名称 | string |  |
|   description | 模型描述 | string |  |
|   model | 模型标识 | string |  |
|   type | 模型类型，可用值: Completions, Chat, Multi, Edits, Images, Embeddings, Audio, Other | string |  |
|   isReasonModel | 是否为推理模型 | integer(int32) |  |
|   networkType | 网络类型，可用值: Internet, Intranet | string |  |
|   functionCall | 函数调用支持程度，可用值: Unsupported, CallSupported, StreamCallSupported | string |  |
|   maxTokens | token上限 | integer(int32) |  |
|   maxContextTokens | 上下文token上限 | integer(int32) |  |
|   apiProtocol | 接口协议，可用值: OpenAI, Ollama, Zhipu, Anthropic | string |  |
|   apiInfoList | API列表 | array | ApiInfo |
|     url | 接口地址 | string |  |
|     key | 接口密钥 | string |  |
|     weight | 权重 | integer(int32) |  |
|   strategy | 调用策略，可用值: RoundRobin, WeightedRoundRobin, LeastConnections, WeightedLeastConnections, Random, ResponseTime | string |  |
|   dimension | 向量维度 | integer(int32) |  |
|   modified | 修改时间 | string(date-time) |  |
|   created | 创建时间 | string(date-time) |  |
|   creator | 创建者信息 | CreatorDto |  |
|     userId | 用户ID | integer(int64) |  |
|     userName | 用户名 | string |  |
|     nickName | 昵称 | string |  |
|     avatar | 头像 | string |  |
|   enabled | 是否启用 | integer(int32) |  |
|   accessControl | 访问控制，0-不管控，1-管控 | integer(int32) |  |
|   usageScenarios | 可使用的业务场景 | array | string |
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
			"id": 1,
			"tenantId": 1,
			"spaceId": null,
			"scope": "Tenant",
			"name": "更新后的GPT-3.5",
			"description": null,
			"model": "gpt-3.5-turbo",
			"type": "Chat",
			"isReasonModel": 0,
			"networkType": "Internet",
			"functionCall": "CallSupported",
			"maxTokens": 4096,
			"maxContextTokens": 128000,
			"apiProtocol": "OpenAI",
			"apiInfoList": [
				{
					"url": "https://api.openai.com/v1",
					"key": "sk-updated-key",
					"weight": 1
				}
			],
			"strategy": "RoundRobin",
			"dimension": 1536,
			"enabled": 1,
			"accessControl": 0,
			"usageScenarios": ["Workflow", "TaskAgent", "PageApp", "ChatBot", "OpenApi"]
		}
	],
	"tid": "123456",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/model/list' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"success","data":[...],"tid":"123456","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 查询模型列表 | 0000 | 成功，返回全部模型配置 |

**TS模板示例**

```ts
// API信息
export interface ApiInfo {
  url: string;
  key: string;
  weight: number;
}

// 创建者信息
export interface CreatorDto {
  userId: number;
  userName: string;
  nickName: string;
  avatar: string;
}

// 模型配置
export interface ModelConfigDto {
  id: number;
  tenantId: number;
  spaceId: number | null;
  scope: 'Space' | 'Tenant' | 'Global';
  name: string;
  description: string | null;
  model: string;
  type: 'Completions' | 'Chat' | 'Multi' | 'Edits' | 'Images' | 'Embeddings' | 'Audio' | 'Other';
  isReasonModel: number;
  networkType: 'Internet' | 'Intranet';
  functionCall: 'Unsupported' | 'CallSupported' | 'StreamCallSupported';
  maxTokens: number;
  maxContextTokens: number;
  apiProtocol: 'OpenAI' | 'Ollama' | 'Zhipu' | 'Anthropic';
  apiInfoList: ApiInfo[];
  strategy: 'RoundRobin' | 'WeightedRoundRobin' | 'LeastConnections' | 'WeightedLeastConnections' | 'Random' | 'ResponseTime';
  dimension: number;
  modified: string;
  created: string;
  creator: CreatorDto;
  enabled: number;
  accessControl: number;
  usageScenarios: ('PageApp' | 'TaskAgent' | 'ChatBot' | 'Workflow' | 'OpenApi')[];
}

// 响应接口
export interface ModelListRes {
  code: string;
  displayCode: string;
  message: string;
  data: ModelConfigDto[];
  tid: string;
  success: boolean;
}

/** 
 * 查询模型配置列表
 * @returns
 */
export function getModelList(): Promise<ModelListRes> {
  return request.get(`/api/v1/system/model/list`);
}
```
