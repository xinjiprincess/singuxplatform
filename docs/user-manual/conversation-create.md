# 创建会话

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/chat/conversation/add`

**请求方式**:`POST`

**请求数据类型**:`application/json`

**响应数据类型**:`*/*`

**接口描述**:

创建与智能体的新会话

**请求示例**:

```javascript
{
  "agentId": 1596,
  "variables": {"key1": "value1"},
  "devMode": true
}
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**请求体参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| agentId | 智能体ID | 是 | integer(int64) |
| variables | 会话变量内容 | 否 | object |
| devMode | 开发模式，为true时，智能体无需发布，变更实时生效 | 否 | boolean |

**响应参数**:

| 参数名称 | 参数说明 | 类型 | schema |
| --- | --- | --- | --- |
| code | 业务状态码，0000 表示成功，其余失败 | string |  |
| displayCode | 源系统状态码，用于问题跟踪 | string |  |
| message | 错误描述信息 | string |  |
| data | 创建的会话ID | integer(int64) |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": 1545548,
	"tid": "2734711776085221044",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/chat/conversation/add' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{"agentId": 1596, "variables": {"key1": "value1"}, "devMode": true}'

{"code":"0000","displayCode":"0000","message":"success","data":1545548,"tid":"2734711776085221044","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 创建已发布智能体的会话 | 0000 | 成功，返回会话ID |
| 2 | 创建会话（携带变量和开发模式） | 0000 | 成功，返回会话ID |
| 3 | 创建不存在或已下架智能体的会话 | 4000 | 失败，提示"智能体不存在或已下架" |

**TS模板示例**

```ts
// 参数接口
export interface ConvCreateDto {
  /* 智能体ID */
  agentId: number;
  /* 会话变量内容 */
  variables?: Record<string, unknown>;
  /* 开发模式，为true时，智能体无需发布，变更实时生效 */
  devMode?: boolean;
}

// 响应接口
export interface ConversationCreateRes {
  code: string;
  displayCode: string;
  message: string;
  data: number;
  tid: string;
  success: boolean;
}

/** 
 * 创建会话
 * @param {ConvCreateDto} params 
 * @returns
 */
export function createConversation(params: ConvCreateDto): Promise<ConversationCreateRes> {
  return request.post(`/api/v1/chat/conversation/add`, params);
}
```
