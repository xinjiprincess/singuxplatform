# 清除用户ticket认证

> 更新：2026-10-04。本章为功能与操作参考，实际菜单取决于服务器授权和环境配置。界面存在不表示生产能力已验收，环境边界以项目操作指南为准。 接口未对线上执行写入验证；服务地址与密钥需替换为实际值。

## 接口信息

**接口地址**:`/api/v1/system/user/{id}/ticket/clear`

**请求方式**:`POST`

**请求数据类型**:`无`

**响应数据类型**:`*/*`

**接口描述**:

清除指定用户通过 ticket 获得的认证信息

**请求示例**:

```
POST /api/v1/system/user/1776073061/ticket/clear
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
	"tid": "1632291776079192210",
	"success": true
}
```

**CURL示例**

```shell
curl 'http://127.0.0.1:8081/api/v1/system/user/1776073061/ticket/clear' \
  -X POST \
  -H 'Authorization: Bearer ak-REPLACE_WITH_API_KEY'

{"code":"0000","displayCode":"0000","message":"成功","data":null,"tid":"1632291776079192210","success":true}
```

**测试用例**

| # | 场景 | 状态码 | 结果 |
| --- | --- | --- | --- |
| 1 | 清除已有用户的 ticket | 0000 | 成功 |
| 2 | 清除不存在的用户的 ticket | 0000 | 成功（幂等） |

**TS模板示例**

```ts
// 响应接口
export interface ClearTicketRes {
  code: string;
  displayCode: string;
  message: string;
  data: object | null;
  tid: string;
  success: boolean;
}

/** 
 * 清除用户ticket认证
 * @param {number} id - 用户ID
 * @returns
 */
export function clearTicket(id: number): Promise<ClearTicketRes> {
  return request.post(`/api/v1/system/user/${id}/ticket/clear`);
}
```
