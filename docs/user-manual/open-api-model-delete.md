# 删除模型配置

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/model/{modelId}/delete`

**请求方式**:`POST`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

删除指定模型的配置信息。默认模型不允许删除。

> 注意：请勿删除系统现有数据，建议先通过 `/api/v1/system/model/add` 创建测试模型再进行删除操作。

**请求示例**:

```
POST /api/v1/system/model/100000002/delete
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
	"tid": "5531291776081066058",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/model/100000002/delete' \
  -X POST \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"3401601776082479114","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 删除新创建的模型 | 0000 | 成功 |

#### 删除新创建的模型

先通过添加模型接口创建测试模型，再进行删除：

```shell
curl 'http://127.0.0.1:8081/api/v1/system/model/add' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY' \
  --data-raw '{
  "name": "删除测试模型",
  "model": "gpt-delete-test-99",
  "type": "Chat",
  "apiProtocol": "OpenAI",
  "strategy": "RoundRobin",
  "apiInfoList": [
    {"url": "https://api.test.com", "key": "sk-delete-99", "weight": 1}
  ],
  "enabled": 1
}'

{"code":"0000","displayCode":"0000","message":"success","data":100000002,"tid":"4914911776082381653","success":true}
```

```shell
curl 'http://127.0.0.1:8081/api/v1/system/model/100000002/delete' \
  -X POST \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"3401601776082479114","success":true}
```

**TS模板示例**

```ts
// 响应接口
export interface DeleteModelRes {
  code: string;
  displayCode: string;
  message: string;
  data: object | null;
  tid: string;
  success: boolean;
}

/** 
 * 删除模型配置
 * @param {number} modelId - 模型ID
 * @returns
 */
export function deleteModel(modelId: number): Promise<DeleteModelRes> {
  return request.post(`/api/v1/system/model/${modelId}/delete`);
}
```
