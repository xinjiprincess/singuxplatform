# 创建指定用户的认证ticket

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/user/{id}/ticket/create`

**请求方式**:`POST`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

为指定用户创建认证 ticket，用于用户免登录认证

**请求示例**:

```
POST /api/v1/system/user/1776073061/ticket/create
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
| data | 认证ticket | string |  |
| tid | 跟踪唯一标识 | string |  |
| success |  | boolean |  |

**响应示例**:

```javascript
{
	"code": "0000",
	"displayCode": "0000",
	"message": "success",
	"data": "846f39681cf44166a46ab643a2e0950d",
	"tid": "8659031776079107595",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/1776073061/ticket/create' \
  -X POST \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"success","data":"846f39681cf44166a46ab643a2e0950d","tid":"8659031776079107595","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 创建已有用户的 ticket | 0000 | 成功，返回 ticket 字符串 |
| 2 | 创建不存在的用户的 ticket | 4000 | 失败，返回 Error user id |

#### 失败用例

**用户ID不存在**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/99999999/ticket/create' \
  -X POST \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"4000","displayCode":"4000","message":"Error user id","data":null,"tid":"3483351776079108404","success":false}
```

**TS模板示例**

```ts
// 响应接口
export interface CreateTicketRes {
  code: string;
  displayCode: string;
  message: string;
  data: string;
  tid: string;
  success: boolean;
}

/** 
 * 创建指定用户的认证ticket
 * @param {number} id - 用户ID
 * @returns
 */
export function createTicket(id: number): Promise<CreateTicketRes> {
  return request.post(`/api/v1/system/user/${id}/ticket/create`);
}
```
