# 启用用户

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/user/{id}/enable`

**请求方式**:`POST`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

通过用户ID启用用户，启用后用户状态变为 `Enabled`

**请求示例**:

```
POST /api/v1/system/user/1776073061/enable
```

## 请求参数

**请求头**

| 参数名 | 类型 | 必填 | 描述 | 示例值 |
| --- | --- | --- | --- | --- |
| Authorization | string | 是 | API Key | `Bearer ak-REPLACE_WITH_API_KEY` |

**路径参数**:

| 参数名称 | 参数说明 | 是否必须 | 数据类型 |
| --- | --- | --- | --- |
| id | 用户ID | 是 | integer(int64) |

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
	"tid": "4477891776078779982",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/1776073061/enable' \
  -X POST \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"4477891776078779982","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 启用已禁用的用户 | 0000 | 成功，用户状态变为 Enabled |
| 2 | 启用不存在的用户 | 0000 | 成功（幂等） |
| 3 | 重复启用已启用的用户 | 0000 | 成功（幂等） |

#### 验证用户状态

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/detail?id=1776073061' \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"status":"Enabled","id":1776073061,"userName":"更新后的用户名"}
```

**TS模板示例**

```ts
// 响应接口
export interface EnableUserRes {
  code: string;
  displayCode: string;
  message: string;
  data: object | null;
  tid: string;
  success: boolean;
}

/** 
 * 启用用户
 * @param {number} id - 用户ID
 * @returns
 */
export function enableUser(id: number): Promise<EnableUserRes> {
  return request.post(`/api/v1/system/user/${id}/enable`);
}
```
