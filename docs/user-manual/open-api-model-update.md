# 更新模型配置

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/model/{id}/update`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`*/*`

**接口描述**:

更新指定模型配置

**请求示例**:

```javascript
{
  "name": "更新后的GPT-3.5",
  "model": "gpt-3.5-turbo",
  "type": "Chat",
  "apiProtocol": "OpenAI",
  "strategy": "RoundRobin",
  "apiInfoList": [
    {"url": "https://api.openai.com/v1", "key": "sk-updated-key", "weight": 1}
  ],
  "enabled": 1
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
| id | 模型ID | 是 | integer(int64) |

**请求体参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| name | 模型名称 | 是 | string |
| description | 模型描述 | 否 | string |
| model | 模型标识 | 是 | string |
| type | 模型类型，可用值: Completions, Chat, Multi, Edits, Images, Embeddings, Audio, Other | 是 | string |
| maxTokens | 最大输出token数 | 否 | integer(int32) |
| maxContextTokens | 上下文最大输出token数 | 否 | integer(int32) |
| apiProtocol | 模型接口协议，可用值: OpenAI, Ollama, Zhipu, Anthropic | 是 | string |
| apiInfoList | API列表 | 是 | array |
|   url | 接口地址 | 否 | string |
|   key | 接口密钥 | 否 | string |
|   weight | 权重 | 否 | integer(int32) |
| strategy | 接口调用策略，可用值: RoundRobin, WeightedRoundRobin, LeastConnections, WeightedLeastConnections, Random, ResponseTime | 是 | string |
| dimension | 向量维度 | 否 | integer(int32) |
| functionCall | 函数调用支持，可用值: Unsupported, CallSupported, StreamCallSupported | 否 | string |
| isReasonModel | 是否为推理模型，0 否；1 是 | 否 | integer(int32) |
| enabled | 是否启用，1-启用，0-禁用 | 否 | integer(int32) |
| accessControl | 访问控制，0-不管控，1-管控 | 否 | integer(int32) |
| usageScenarios | 可使用的业务场景，可用值: PageApp, TaskAgent, ChatBot, Workflow, OpenApi | 否 | array |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 返回的具体业务数据 | object |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "成功",
	"data": null,
	"tid": "9514941776080834412",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/model/100000002/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "name": "更新后的测试模型",
  "model": "gpt-delete-test-99",
  "type": "Chat",
  "apiProtocol": "OpenAI",
  "strategy": "WeightedRoundRobin",
  "apiInfoList": [
    {"url": "https://api.test.com", "key": "sk-updated-key", "weight": 1}
  ],
  "enabled": 1
}'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"1205451776082393098","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 更新新创建的模型 | 0000 | 成功 |

#### 更新模型配置

```shell
curl 'http://127.0.0.1:8081/api/v1/system/model/100000002/update' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "name": "更新后的测试模型",
  "model": "gpt-delete-test-99",
  "type": "Chat",
  "apiProtocol": "OpenAI",
  "strategy": "WeightedRoundRobin",
  "apiInfoList": [
    {"url": "https://api.test.com", "key": "sk-updated-key", "weight": 1}
  ],
  "enabled": 1
}'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"1205451776082393098","success":true}
```

**TS模板示例**

```ts
// API信息
export interface ApiInfo {
  /* 接口地址 */
  url?: string;
  /* 接口密钥 */
  key?: string;
  /* 权重 */
  weight?: number;
}

// 参数接口
export interface ModelConfigUpdateDto {
  /* 模型名称 */
  name: string;
  /* 模型描述 */
  description?: string;
  /* 模型标识 */
  model: string;
  /* 模型类型 */
  type: 'Completions' | 'Chat' | 'Multi' | 'Edits' | 'Images' | 'Embeddings' | 'Audio' | 'Other';
  /* 最大输出token数 */
  maxTokens?: number;
  /* 上下文最大输出token数 */
  maxContextTokens?: number;
  /* 接口协议 */
  apiProtocol: 'OpenAI' | 'Ollama' | 'Zhipu' | 'Anthropic';
  /* API列表 */
  apiInfoList: ApiInfo[];
  /* 调用策略 */
  strategy: 'RoundRobin' | 'WeightedRoundRobin' | 'LeastConnections' | 'WeightedLeastConnections' | 'Random' | 'ResponseTime';
  /* 向量维度 */
  dimension?: number;
  /* 函数调用支持 */
  functionCall?: 'Unsupported' | 'CallSupported' | 'StreamCallSupported';
  /* 是否为推理模型 */
  isReasonModel?: number;
  /* 是否启用 */
  enabled?: number;
  /* 访问控制 */
  accessControl?: number;
  /* 使用场景 */
  usageScenarios?: ('PageApp' | 'TaskAgent' | 'ChatBot' | 'Workflow' | 'OpenApi')[];
}

// 响应接口
export interface UpdateModelRes {
  code: string;
  displayCode: string;
  message: string;
  data: object | null;
  tid: string;
  success: boolean;
}

/** 
 * 更新模型配置
 * @param {number} id - 模型ID
 * @param {ModelConfigUpdateDto} params 
 * @returns
 */
export function updateModel(id: number, params: ModelConfigUpdateDto): Promise<UpdateModelRes> {
  return request.post(`/api/v1/system/model/${id}/update`, params);
}
```
